from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.estoque.models import FormaVendaProduto, MovimentacaoEstoque, Produto
from apps.estoque.services import cancelar_movimentacao, saida_estoque
from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from apps.financeiro.services import cancelar_lancamento_financeiro, criar_lancamento_financeiro

from ..models import ItemVenda, Venda, ZERO_MONEY, money


def venda_snapshot(venda: Venda) -> dict[str, Any]:
    return {
        "id": str(venda.pk),
        "company_id": str(venda.company_id),
        "numero": venda.numero,
        "cliente_id": str(venda.cliente_id) if venda.cliente_id else None,
        "status": venda.status,
        "valor_subtotal": str(venda.valor_subtotal),
        "desconto": str(venda.desconto),
        "valor_total": str(venda.valor_total),
        "forma_pagamento": venda.forma_pagamento,
        "conta_financeira_id": str(venda.conta_financeira_id),
        "observacao": venda.observacao,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _get_or_create_categoria_vendas(*, company) -> CategoriaFinanceira:
    categoria, _ = CategoriaFinanceira.objects.get_or_create(
        company=company,
        nome="Venda Balcão",
        tipo=CategoriaFinanceira.TIPO_RECEITA,
        deleted_at__isnull=True,
        defaults={"descricao": "Receitas de vendas diretas no balcão", "ativa": True},
    )
    return categoria


def _locked_produto(*, produto_id, company_id) -> Produto:
    try:
        return Produto.objects.get(
            pk=produto_id,
            company_id=company_id,
            deleted_at__isnull=True,
        )
    except Produto.DoesNotExist:
        raise NotFound(f"Produto {produto_id} não encontrado.")


def _get_forma_venda(*, forma_venda_id, produto: Produto, company_id) -> FormaVendaProduto | None:
    if not forma_venda_id:
        return None
    # Aceita tanto UUID quanto instância já resolvida pelo serializer
    pk = forma_venda_id.pk if isinstance(forma_venda_id, FormaVendaProduto) else forma_venda_id
    try:
        forma = FormaVendaProduto.objects.get(
            pk=pk,
            produto=produto,
            company_id=company_id,
            deleted_at__isnull=True,
        )
    except FormaVendaProduto.DoesNotExist:
        raise ValidationError({"forma_venda": "Forma de venda não encontrada ou não pertence ao produto."})
    if not forma.ativo or not forma.is_active:
        raise ValidationError({"forma_venda": "Forma de venda inativa."})
    return forma


@transaction.atomic
def criar_venda(*, user, data: dict[str, Any], request=None) -> Venda:
    require_company(user)
    company_id = user.company_id

    itens_data = data.get("itens", [])
    if not itens_data:
        raise ValidationError({"itens": "A venda deve conter pelo menos 1 item."})

    conta_financeira = data["conta_financeira"]
    forma_pagamento = data["forma_pagamento"]
    desconto = money(Decimal(str(data.get("desconto", "0.00"))))
    cliente = data.get("cliente")
    observacao = (data.get("observacao") or "").strip()

    if cliente and getattr(cliente, "company_id", None) != company_id:
        raise ValidationError({"cliente": "Cliente não pertence à empresa."})
    if conta_financeira.company_id != company_id:
        raise ValidationError({"conta_financeira": "Conta financeira não pertence à empresa."})
    if not conta_financeira.ativo:
        raise ValidationError({"conta_financeira": "Conta financeira inativa."})

    # Criar venda provisória para gerar numero a partir do pk
    venda = Venda(
        company=user.company,
        numero="",  # preenchido após save
        cliente=cliente,
        status=Venda.STATUS_CONCLUIDA,
        valor_subtotal=ZERO_MONEY,
        desconto=desconto,
        valor_total=ZERO_MONEY,
        forma_pagamento=forma_pagamento,
        conta_financeira=conta_financeira,
        observacao=observacao,
        created_by=user,
    )
    venda.save()
    venda.numero = f"PDV-{str(venda.pk)[:8].upper()}"
    venda.save(update_fields=["numero", "updated_at"])

    subtotal = ZERO_MONEY

    for item_data in itens_data:
        produto = _locked_produto(produto_id=item_data["produto"], company_id=company_id)
        forma_venda = _get_forma_venda(
            forma_venda_id=item_data.get("forma_venda"),
            produto=produto,
            company_id=company_id,
        )

        quantidade_informada = Decimal(str(item_data["quantidade_informada"])).quantize(Decimal("0.001"))
        if quantidade_informada <= Decimal("0.000"):
            raise ValidationError({"quantidade_informada": "Quantidade deve ser maior que zero."})

        if forma_venda is not None:
            quantidade = forma_venda.converter(quantidade_informada)
        else:
            quantidade = quantidade_informada

        preco_unitario = money(Decimal(str(item_data["preco_unitario"])))
        if preco_unitario < ZERO_MONEY:
            raise ValidationError({"preco_unitario": "Preço unitário não pode ser negativo."})

        subtotal_item = money(quantidade_informada * preco_unitario)
        subtotal += subtotal_item

        mov = saida_estoque(
            user=user,
            produto=produto,
            quantidade=quantidade,
            forma_venda=forma_venda,
            quantidade_informada=quantidade_informada if forma_venda else None,
            motivo=f"Venda {venda.numero}",
            observacao=observacao,
            request=request,
        )

        item = ItemVenda(
            company=user.company,
            venda=venda,
            produto=produto,
            forma_venda=forma_venda,
            quantidade_informada=quantidade_informada,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            subtotal=subtotal_item,
            movimentacao_estoque=mov,
        )
        _full_clean_or_400(item)
        item.save()

    valor_total = money(subtotal - desconto)
    if valor_total <= ZERO_MONEY:
        raise ValidationError({"desconto": "Desconto não pode exceder o subtotal."})

    categoria = _get_or_create_categoria_vendas(company=user.company)

    lancamento = criar_lancamento_financeiro(
        user=user,
        conta_financeira=conta_financeira,
        categoria=categoria,
        tipo=LancamentoFinanceiro.TIPO_ENTRADA,
        valor=valor_total,
        descricao=f"Venda {venda.numero}",
        origem_tipo=LancamentoFinanceiro.ORIGEM_MANUAL,
        origem_id=venda.pk,
        forma_pagamento=forma_pagamento,
        metadata={"origem": "VENDA", "venda_id": str(venda.pk), "venda_numero": venda.numero},
        request=request,
    )

    venda.valor_subtotal = subtotal
    venda.valor_total = valor_total
    venda.lancamento_financeiro = lancamento
    venda._allow_update = True  # bypass imutabilidade se necessário
    venda.save(update_fields=["valor_subtotal", "valor_total", "lancamento_financeiro", "updated_at"])

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=venda,
        after=venda_snapshot(venda),
        request=request,
    )

    return venda


@transaction.atomic
def cancelar_venda(*, user, venda: Venda, motivo: str, request=None) -> Venda:
    require_company(user)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})
    if venda.company_id != user.company_id:
        raise ValidationError({"venda": "Venda não pertence à empresa."})

    try:
        venda_locked = (
            Venda.objects.select_for_update(of=("self",))
            .get(pk=venda.pk, company_id=user.company_id, deleted_at__isnull=True)
        )
    except Venda.DoesNotExist:
        raise NotFound("Venda não encontrada.")

    if venda_locked.status == Venda.STATUS_CANCELADA:
        raise ValidationError({"status": "Venda já foi cancelada."})

    before = venda_snapshot(venda_locked)

    # Reverter movimentações de estoque
    itens = (
        ItemVenda.objects.select_related("movimentacao_estoque")
        .filter(venda=venda_locked, deleted_at__isnull=True)
    )
    for item in itens:
        mov = item.movimentacao_estoque
        if mov and mov.status == MovimentacaoEstoque.STATUS_ATIVA:
            cancelar_movimentacao(
                user=user,
                movimentacao=mov,
                motivo=f"Cancelamento da venda {venda_locked.numero}: {motivo}",
                request=request,
            )

    # Estornar lançamento financeiro
    if venda_locked.lancamento_financeiro_id:
        lancamento = venda_locked.lancamento_financeiro
        if lancamento.status == LancamentoFinanceiro.STATUS_CONFIRMADO:
            cancelar_lancamento_financeiro(
                user=user,
                lancamento=lancamento,
                motivo=f"Cancelamento da venda {venda_locked.numero}: {motivo}",
                request=request,
            )

    venda_locked.status = Venda.STATUS_CANCELADA
    venda_locked.cancelled_by = user
    venda_locked.cancelled_at = timezone.now()
    venda_locked.motivo_cancelamento = motivo
    venda_locked.save(
        update_fields=["status", "cancelled_by", "cancelled_at", "motivo_cancelamento", "updated_at"]
    )

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=venda_locked,
        before=before,
        after=venda_snapshot(venda_locked),
        request=request,
    )

    return venda_locked
