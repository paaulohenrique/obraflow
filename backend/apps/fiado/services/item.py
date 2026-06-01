from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.estoque.models import Produto
from apps.estoque.services import cancelar_movimentacao, saida_estoque

from ..models import ContaFiado, HistoricoFiado, ItemFiado, ZERO_MONEY, item_subtotal, money
from .conta import (
    _ensure_same_company,
    _full_clean_or_400,
    _locked_cliente,
    _locked_conta,
    _save_immutable_update,
    _save_model,
    cliente_snapshot,
    conta_snapshot,
    criar_historico_fiado,
    fechar_conta_se_quitada,
    item_snapshot,
    validar_cliente_pode_comprar,
)


def _locked_item(*, item_id, company_id) -> ItemFiado:
    try:
        return (
            ItemFiado.objects.select_for_update(of=("self",))
            .select_related("conta", "produto", "movimentacao_estoque")
            .get(pk=item_id, company_id=company_id, deleted_at__isnull=True)
        )
    except ItemFiado.DoesNotExist:
        raise NotFound("Item fiado não encontrado.")


def _conta_cliente_id(*, conta_id, company_id):
    try:
        return ContaFiado.objects.only("cliente_id").get(
            pk=conta_id,
            company_id=company_id,
            deleted_at__isnull=True,
        ).cliente_id
    except ContaFiado.DoesNotExist:
        raise NotFound("Conta fiado não encontrada.")


def _existing_item_by_key(*, company_id, idempotency_key: str) -> ItemFiado | None:
    if not idempotency_key:
        return None
    return (
        ItemFiado.objects.select_related("conta", "produto", "movimentacao_estoque")
        .filter(
            company_id=company_id,
            idempotency_key=idempotency_key,
            deleted_at__isnull=True,
        )
        .first()
    )


@transaction.atomic
def adicionar_item_fiado(
    *,
    user,
    conta: ContaFiado,
    data: dict[str, Any],
    request=None,
) -> ItemFiado:
    require_company(user)
    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta")

    idempotency_key = (data.get("idempotency_key") or "").strip()
    existing = _existing_item_by_key(
        company_id=user.company_id,
        idempotency_key=idempotency_key,
    )
    if existing:
        return existing

    cliente = _locked_cliente(cliente_id=conta.cliente_id, company_id=user.company_id)
    conta = _locked_conta(conta_id=conta.pk, company_id=user.company_id)
    if conta.cliente_id != cliente.pk:
        raise ValidationError({"conta": "Conta inconsistente com o cliente informado."})
    if conta.status != ContaFiado.STATUS_ABERTA:
        raise ValidationError({"status": "Somente conta aberta pode receber item."})
    validar_cliente_pode_comprar(cliente)

    from apps.estoque.models import FormaVendaProduto

    produto: Produto = data["produto"]
    _ensure_same_company(obj=produto, company_id=user.company_id, field="produto")
    if not produto.is_active:
        raise ValidationError({"produto": "Produto inativo não pode ser vendido no fiado."})

    forma_venda: FormaVendaProduto | None = data.get("forma_venda")
    if forma_venda is not None:
        if forma_venda.company_id != user.company_id:
            raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})
        if forma_venda.produto_id != produto.pk:
            raise ValidationError({"forma_venda": "Forma de venda não pertence a este produto."})
        if not forma_venda.ativo:
            raise ValidationError({"forma_venda": "Forma de venda está inativa."})

    quantidade_informada: Decimal | None = data.get("quantidade_informada")
    if forma_venda is not None and quantidade_informada is not None:
        quantidade = forma_venda.converter(quantidade_informada)
    else:
        quantidade = data["quantidade"]
        quantidade_informada = None

    preco_unitario = money(
        data["preco_unitario"]
        if data.get("preco_unitario") is not None
        else (forma_venda.preco_venda if forma_venda else produto.preco_venda)
    )
    subtotal = item_subtotal(quantidade=quantidade, preco_unitario=preco_unitario)

    if subtotal > ZERO_MONEY and cliente.limite_credito <= ZERO_MONEY:
        raise ValidationError({"limite_credito": "Cliente não possui limite de crédito."})
    if money(cliente.saldo_devedor + subtotal) > money(cliente.limite_credito):
        raise ValidationError({"limite_credito": "Limite de crédito insuficiente."})

    item = ItemFiado(
        company=user.company,
        conta=conta,
        produto=produto,
        forma_venda=forma_venda,
        quantidade_informada=quantidade_informada,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        subtotal=subtotal,
        observacao=data.get("observacao", ""),
        created_by=user,
        idempotency_key=idempotency_key,
    )
    _full_clean_or_400(item)
    item.save()

    movimentacao = saida_estoque(
        user=user,
        produto=produto,
        quantidade=quantidade,
        motivo="Venda fiado",
        observacao=item.observacao,
        forma_venda=forma_venda,
        quantidade_informada=quantidade_informada,
        idempotency_key=f"fiado_item:{item.pk}",
        metadata={
            "fiado_item_id": str(item.pk),
            "fiado_conta_id": str(conta.pk),
            "cliente_id": str(cliente.pk),
        },
        request=request,
    )

    item.movimentacao_estoque = movimentacao
    _save_immutable_update(item, update_fields=["movimentacao_estoque"])

    conta_before = conta_snapshot(conta)
    cliente_before = cliente_snapshot(cliente)

    conta.valor_total = money(conta.valor_total + subtotal)
    conta.valor_restante = money(conta.valor_total - conta.valor_pago)
    _save_model(conta, update_fields=["valor_total", "valor_restante"])

    cliente.saldo_devedor = money(cliente.saldo_devedor + subtotal)
    cliente.save(update_fields=["saldo_devedor", "updated_at"])

    item_after = item_snapshot(item)
    conta_after = conta_snapshot(conta)
    cliente_after = cliente_snapshot(cliente)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=item,
        after=item_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=conta_before,
        after=conta_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=cliente_before,
        after=cliente_after,
        request=request,
    )
    criar_historico_fiado(
        user=user,
        conta=conta,
        item=item,
        evento=HistoricoFiado.EVENTO_ITEM_ADICIONADO,
        descricao="Item adicionado à conta fiado.",
        after=item_after,
        metadata={
            "conta": conta_after,
            "cliente": cliente_after,
            "movimentacao_estoque_id": str(movimentacao.pk),
        },
    )
    return item


@transaction.atomic
def cancelar_item_fiado(
    *,
    user,
    item: ItemFiado,
    motivo: str,
    observacao: str = "",
    request=None,
) -> ItemFiado:
    require_company(user)
    _ensure_same_company(obj=item, company_id=user.company_id, field="item")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})

    cliente_id = _conta_cliente_id(conta_id=item.conta_id, company_id=user.company_id)
    cliente = _locked_cliente(cliente_id=cliente_id, company_id=user.company_id)
    conta = _locked_conta(conta_id=item.conta_id, company_id=user.company_id)
    item = _locked_item(item_id=item.pk, company_id=user.company_id)

    if item.conta_id != conta.pk or conta.cliente_id != cliente.pk:
        raise ValidationError({"item": "Item inconsistente com a conta informada."})
    if conta.status == ContaFiado.STATUS_CANCELADA:
        raise ValidationError({"status": "Conta cancelada não aceita cancelamento de item."})
    if item.status == ItemFiado.STATUS_CANCELADO:
        raise ValidationError({"status": "Item fiado já está cancelado."})
    if not item.movimentacao_estoque_id:
        raise ValidationError({"movimentacao_estoque": "Item não possui baixa de estoque."})

    novo_total = money(conta.valor_total - item.subtotal)
    if conta.valor_pago > novo_total:
        raise ValidationError({
            "item": "Cancelamento deixaria pagamentos maiores que o total da conta."
        })
    if cliente.saldo_devedor < item.subtotal and cliente.saldo_devedor != ZERO_MONEY:
        raise ValidationError({"cliente": "Saldo devedor inconsistente para cancelamento."})

    item_before = item_snapshot(item)
    conta_before = conta_snapshot(conta)
    cliente_before = cliente_snapshot(cliente)

    cancelamento = cancelar_movimentacao(
        user=user,
        movimentacao=item.movimentacao_estoque,
        motivo=motivo,
        observacao=observacao,
        idempotency_key=f"fiado_item_cancel:{item.pk}",
        metadata={
            "fiado_item_id": str(item.pk),
            "fiado_conta_id": str(conta.pk),
            "cliente_id": str(cliente.pk),
        },
        request=request,
    )

    item.status = ItemFiado.STATUS_CANCELADO
    item.cancelled_by = user
    item.cancelled_at = timezone.now()
    item.motivo_cancelamento = motivo
    item.movimentacao_cancelamento = cancelamento
    _save_immutable_update(
        item,
        update_fields=[
            "status",
            "cancelled_by",
            "cancelled_at",
            "motivo_cancelamento",
            "movimentacao_cancelamento",
        ],
    )

    conta.valor_total = novo_total
    conta.valor_restante = money(conta.valor_total - conta.valor_pago)
    _save_model(conta, update_fields=["valor_total", "valor_restante"])

    cliente.saldo_devedor = money(cliente.saldo_devedor - item.subtotal)
    if cliente.saldo_devedor < ZERO_MONEY:
        raise ValidationError({"cliente": "Saldo devedor não pode ficar negativo."})
    cliente.save(update_fields=["saldo_devedor", "updated_at"])

    item_after = item_snapshot(item)
    conta_after = conta_snapshot(conta)
    cliente_after = cliente_snapshot(cliente)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=item,
        before=item_before,
        after=item_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=conta_before,
        after=conta_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=cliente_before,
        after=cliente_after,
        request=request,
    )
    criar_historico_fiado(
        user=user,
        conta=conta,
        item=item,
        evento=HistoricoFiado.EVENTO_ITEM_CANCELADO,
        descricao="Item da conta fiado cancelado.",
        before=item_before,
        after=item_after,
        metadata={
            "conta": conta_after,
            "cliente": cliente_after,
            "movimentacao_cancelamento_id": str(cancelamento.pk),
            "observacao": observacao,
        },
    )
    fechar_conta_se_quitada(user=user, conta=conta, request=request)
    return item
