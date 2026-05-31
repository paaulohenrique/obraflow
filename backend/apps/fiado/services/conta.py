from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.clientes.models import Cliente
from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import ContaFiado, HistoricoFiado, ItemFiado, PagamentoFiado, ZERO_MONEY, money


def cliente_snapshot(cliente: Cliente) -> dict[str, Any]:
    return {
        "id": str(cliente.pk),
        "company_id": str(cliente.company_id),
        "nome": cliente.nome,
        "limite_credito": str(cliente.limite_credito),
        "saldo_devedor": str(cliente.saldo_devedor),
        "bloqueado": cliente.bloqueado,
        "is_active": cliente.is_active,
        "data_ultimo_pagamento": (
            cliente.data_ultimo_pagamento.isoformat()
            if cliente.data_ultimo_pagamento
            else None
        ),
    }


def conta_snapshot(conta: ContaFiado) -> dict[str, Any]:
    return {
        "id": str(conta.pk),
        "company_id": str(conta.company_id),
        "cliente_id": str(conta.cliente_id),
        "status": conta.status,
        "valor_total": str(conta.valor_total),
        "valor_pago": str(conta.valor_pago),
        "valor_restante": str(conta.valor_restante),
        "data_abertura": conta.data_abertura.isoformat() if conta.data_abertura else None,
        "data_vencimento": (
            conta.data_vencimento.isoformat() if conta.data_vencimento else None
        ),
        "data_fechamento": (
            conta.data_fechamento.isoformat() if conta.data_fechamento else None
        ),
        "observacao": conta.observacao,
        "created_by_id": str(conta.created_by_id) if conta.created_by_id else None,
        "closed_by_id": str(conta.closed_by_id) if conta.closed_by_id else None,
        "cancelled_by_id": str(conta.cancelled_by_id) if conta.cancelled_by_id else None,
        "cancelled_at": conta.cancelled_at.isoformat() if conta.cancelled_at else None,
        "motivo_cancelamento": conta.motivo_cancelamento,
        "is_parcial": conta.is_parcial,
        "is_atrasada": conta.is_atrasada,
        "dias_atraso": conta.dias_atraso,
    }


def item_snapshot(item: ItemFiado) -> dict[str, Any]:
    return {
        "id": str(item.pk),
        "company_id": str(item.company_id),
        "conta_id": str(item.conta_id),
        "produto_id": str(item.produto_id),
        "quantidade": str(item.quantidade),
        "preco_unitario": str(item.preco_unitario),
        "subtotal": str(item.subtotal),
        "data_lancamento": item.data_lancamento.isoformat() if item.data_lancamento else None,
        "movimentacao_estoque_id": (
            str(item.movimentacao_estoque_id) if item.movimentacao_estoque_id else None
        ),
        "movimentacao_cancelamento_id": (
            str(item.movimentacao_cancelamento_id)
            if item.movimentacao_cancelamento_id
            else None
        ),
        "status": item.status,
        "created_by_id": str(item.created_by_id) if item.created_by_id else None,
        "cancelled_by_id": str(item.cancelled_by_id) if item.cancelled_by_id else None,
        "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at else None,
        "motivo_cancelamento": item.motivo_cancelamento,
        "observacao": item.observacao,
        "idempotency_key": item.idempotency_key,
    }


def pagamento_snapshot(pagamento: PagamentoFiado) -> dict[str, Any]:
    return {
        "id": str(pagamento.pk),
        "company_id": str(pagamento.company_id),
        "conta_id": str(pagamento.conta_id),
        "valor": str(pagamento.valor),
        "forma_pagamento": pagamento.forma_pagamento,
        "data_pagamento": (
            pagamento.data_pagamento.isoformat() if pagamento.data_pagamento else None
        ),
        "status": pagamento.status,
        "observacao": pagamento.observacao,
        "created_by_id": str(pagamento.created_by_id) if pagamento.created_by_id else None,
        "cancelled_by_id": (
            str(pagamento.cancelled_by_id) if pagamento.cancelled_by_id else None
        ),
        "cancelled_at": (
            pagamento.cancelled_at.isoformat() if pagamento.cancelled_at else None
        ),
        "motivo_cancelamento": pagamento.motivo_cancelamento,
        "idempotency_key": pagamento.idempotency_key,
        "metadata": pagamento.metadata,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _ensure_same_company(*, obj, company_id: Any, field: str) -> None:
    if obj and obj.company_id != company_id:
        raise ValidationError({field: "Objeto não pertence à empresa do usuário."})


def _save_model(obj, *, update_fields: list[str] | None = None) -> None:
    _full_clean_or_400(obj)
    if update_fields is None:
        obj.save()
    else:
        obj.save(update_fields=[*update_fields, "updated_at"])


def _save_immutable_update(obj, *, update_fields: list[str]) -> None:
    _full_clean_or_400(obj)
    obj._allow_update = True
    try:
        obj.save(update_fields=[*update_fields, "updated_at"])
    finally:
        obj._allow_update = False


def criar_historico_fiado(
    *,
    user,
    conta: ContaFiado,
    evento: str,
    descricao: str,
    item: ItemFiado | None = None,
    pagamento: PagamentoFiado | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> HistoricoFiado:
    historico = HistoricoFiado.objects.create(
        company=conta.company,
        conta=conta,
        item=item,
        pagamento=pagamento,
        evento=evento,
        descricao=descricao,
        before=before,
        after=after,
        metadata=metadata or {},
        created_by=user,
    )
    return historico


def _locked_cliente(*, cliente_id, company_id: Any) -> Cliente:
    try:
        return (
            Cliente.objects.select_for_update(of=("self",))
            .get(pk=cliente_id, company_id=company_id, deleted_at__isnull=True)
        )
    except Cliente.DoesNotExist:
        raise NotFound("Cliente não encontrado.")


def _locked_conta(*, conta_id, company_id: Any) -> ContaFiado:
    try:
        return (
            ContaFiado.objects.select_for_update(of=("self",))
            .select_related("cliente", "created_by", "closed_by", "cancelled_by")
            .get(pk=conta_id, company_id=company_id, deleted_at__isnull=True)
        )
    except ContaFiado.DoesNotExist:
        raise NotFound("Conta fiado não encontrada.")


def lock_cliente_e_conta(*, user, conta: ContaFiado) -> tuple[Cliente, ContaFiado]:
    require_company(user)
    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta")
    cliente = _locked_cliente(cliente_id=conta.cliente_id, company_id=user.company_id)
    locked_conta = _locked_conta(conta_id=conta.pk, company_id=user.company_id)
    if locked_conta.cliente_id != cliente.pk:
        raise ValidationError({"conta": "Conta inconsistente com o cliente informado."})
    return cliente, locked_conta


def validar_cliente_pode_comprar(cliente: Cliente) -> None:
    if not cliente.is_active:
        raise ValidationError({"cliente": "Cliente inativo não pode comprar no fiado."})
    if cliente.bloqueado:
        raise ValidationError({"cliente": "Cliente bloqueado não pode comprar no fiado."})


def recalcular_totais_conta(conta: ContaFiado) -> ContaFiado:
    itens_total = (
        ItemFiado.objects.filter(
            conta=conta,
            company_id=conta.company_id,
            status=ItemFiado.STATUS_ATIVO,
            deleted_at__isnull=True,
        ).aggregate(total=Sum("subtotal"))["total"]
        or ZERO_MONEY
    )
    pagamentos_total = (
        PagamentoFiado.objects.filter(
            conta=conta,
            company_id=conta.company_id,
            status=PagamentoFiado.STATUS_CONFIRMADO,
            deleted_at__isnull=True,
        ).aggregate(total=Sum("valor"))["total"]
        or ZERO_MONEY
    )
    itens_total = money(itens_total)
    pagamentos_total = money(pagamentos_total)
    if pagamentos_total > itens_total:
        raise ValidationError({
            "valor_pago": "Pagamentos confirmados não podem exceder o total da conta."
        })
    conta.valor_total = itens_total
    conta.valor_pago = pagamentos_total
    conta.valor_restante = money(itens_total - pagamentos_total)
    _save_model(
        conta,
        update_fields=["valor_total", "valor_pago", "valor_restante"],
    )
    return conta


def fechar_conta_se_quitada(*, user, conta: ContaFiado, request=None) -> ContaFiado:
    if (
        conta.status == ContaFiado.STATUS_ABERTA
        and conta.valor_total > ZERO_MONEY
        and conta.valor_restante == ZERO_MONEY
    ):
        before = conta_snapshot(conta)
        conta.status = ContaFiado.STATUS_FECHADA
        conta.data_fechamento = timezone.now()
        conta.closed_by = user
        _save_model(
            conta,
            update_fields=["status", "data_fechamento", "closed_by"],
        )
        after = conta_snapshot(conta)
        create_audit_log(
            user=user,
            action=AuditLog.ACTION_UPDATE,
            entity=conta,
            before=before,
            after=after,
            request=request,
        )
        criar_historico_fiado(
            user=user,
            conta=conta,
            evento=HistoricoFiado.EVENTO_CONTA_FECHADA,
            descricao="Conta fiado fechada automaticamente por quitação.",
            before=before,
            after=after,
        )
    return conta


def _validate_cliente_for_open(cliente: Cliente) -> None:
    validar_cliente_pode_comprar(cliente)


@transaction.atomic
def abrir_conta_fiado(*, user, data: dict[str, Any], request=None) -> ContaFiado:
    require_company(user)
    cliente = data["cliente"]
    _ensure_same_company(obj=cliente, company_id=user.company_id, field="cliente")
    cliente = _locked_cliente(cliente_id=cliente.pk, company_id=user.company_id)
    _validate_cliente_for_open(cliente)

    if ContaFiado.objects.filter(
        company_id=user.company_id,
        cliente=cliente,
        status=ContaFiado.STATUS_ABERTA,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({"cliente": "Cliente já possui conta fiado aberta."})

    conta = ContaFiado(
        company=user.company,
        cliente=cliente,
        data_vencimento=data.get("data_vencimento"),
        observacao=data.get("observacao", ""),
        created_by=user,
    )
    _full_clean_or_400(conta)
    try:
        conta.save()
    except IntegrityError as exc:
        raise ValidationError({"cliente": "Cliente já possui conta fiado aberta."}) from exc

    after = conta_snapshot(conta)
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=conta,
        after=after,
        request=request,
    )
    criar_historico_fiado(
        user=user,
        conta=conta,
        evento=HistoricoFiado.EVENTO_CONTA_CRIADA,
        descricao="Conta fiado criada.",
        after=after,
    )
    return conta


@transaction.atomic
def update_conta_fiado(
    *,
    user,
    conta: ContaFiado,
    data: dict[str, Any],
    request=None,
) -> ContaFiado:
    cliente, conta = lock_cliente_e_conta(user=user, conta=conta)
    _ = cliente
    if conta.status == ContaFiado.STATUS_CANCELADA:
        raise ValidationError({"status": "Conta cancelada não pode ser alterada."})

    before = conta_snapshot(conta)
    vencimento_before = conta.data_vencimento
    observacao_before = conta.observacao

    if "data_vencimento" in data:
        conta.data_vencimento = data["data_vencimento"]
    if "observacao" in data:
        conta.observacao = data["observacao"]

    _save_model(conta, update_fields=["data_vencimento", "observacao"])
    after = conta_snapshot(conta)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=after,
        request=request,
    )

    if "data_vencimento" in data and vencimento_before != conta.data_vencimento:
        criar_historico_fiado(
            user=user,
            conta=conta,
            evento=HistoricoFiado.EVENTO_VENCIMENTO_ALTERADO,
            descricao="Vencimento da conta fiado alterado.",
            before=before,
            after=after,
        )
    if "observacao" in data and observacao_before != conta.observacao:
        criar_historico_fiado(
            user=user,
            conta=conta,
            evento=HistoricoFiado.EVENTO_OBSERVACAO_ALTERADA,
            descricao="Observação da conta fiado alterada.",
            before=before,
            after=after,
        )
    return conta


@transaction.atomic
def cancelar_conta_fiado(
    *,
    user,
    conta: ContaFiado,
    motivo: str,
    observacao: str = "",
    request=None,
) -> ContaFiado:
    require_company(user)
    if getattr(user, "role", "") != "admin":
        raise ValidationError({"permission": "Somente admin pode cancelar conta fiado."})
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})

    cliente, conta = lock_cliente_e_conta(user=user, conta=conta)
    _ = cliente
    if conta.status == ContaFiado.STATUS_CANCELADA:
        raise ValidationError({"status": "Conta fiado já está cancelada."})
    if PagamentoFiado.objects.filter(
        conta=conta,
        company_id=user.company_id,
        status=PagamentoFiado.STATUS_CONFIRMADO,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({
            "pagamentos": "Conta com pagamentos confirmados não pode ser cancelada na V1."
        })

    from .item import cancelar_item_fiado

    for item in list(
        ItemFiado.objects.filter(
            conta=conta,
            company_id=user.company_id,
            status=ItemFiado.STATUS_ATIVO,
            deleted_at__isnull=True,
        ).select_related("conta", "produto", "movimentacao_estoque")
    ):
        cancelar_item_fiado(
            user=user,
            item=item,
            motivo=motivo,
            observacao=observacao,
            request=request,
        )

    conta = _locked_conta(conta_id=conta.pk, company_id=user.company_id)
    before = conta_snapshot(conta)
    conta.status = ContaFiado.STATUS_CANCELADA
    conta.cancelled_by = user
    conta.cancelled_at = timezone.now()
    conta.motivo_cancelamento = motivo
    _save_model(
        conta,
        update_fields=["status", "cancelled_by", "cancelled_at", "motivo_cancelamento"],
    )
    after = conta_snapshot(conta)
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=after,
        request=request,
    )
    criar_historico_fiado(
        user=user,
        conta=conta,
        evento=HistoricoFiado.EVENTO_CONTA_CANCELADA,
        descricao="Conta fiado cancelada.",
        before=before,
        after=after,
        metadata={"observacao": observacao},
    )
    return conta
