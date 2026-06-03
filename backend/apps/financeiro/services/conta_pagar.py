from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import CategoriaFinanceira, ContaPagar, LancamentoFinanceiro, ZERO_MONEY, money
from .categoria import _ensure_same_company, _full_clean_or_400


def conta_pagar_snapshot(conta: ContaPagar) -> dict[str, Any]:
    return {
        "id": str(conta.pk),
        "company_id": str(conta.company_id),
        "fornecedor_id": str(conta.fornecedor_id) if conta.fornecedor_id else None,
        "descricao": conta.descricao,
        "categoria_id": str(conta.categoria_id),
        "valor_total": str(conta.valor_total),
        "valor_pago": str(conta.valor_pago),
        "valor_restante": str(conta.valor_restante),
        "data_emissao": conta.data_emissao.isoformat(),
        "data_vencimento": conta.data_vencimento.isoformat(),
        "data_pagamento": conta.data_pagamento.isoformat() if conta.data_pagamento else None,
        "status": conta.status,
        "observacao": conta.observacao,
        "created_by_id": str(conta.created_by_id) if conta.created_by_id else None,
        "cancelled_by_id": str(conta.cancelled_by_id) if conta.cancelled_by_id else None,
        "cancelled_at": conta.cancelled_at.isoformat() if conta.cancelled_at else None,
        "motivo_cancelamento": conta.motivo_cancelamento,
    }


def _save_conta_pagar(conta: ContaPagar, *, update_fields: list[str]) -> None:
    try:
        conta.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))
    conta.save(update_fields=[*update_fields, "updated_at"])


def _locked_conta_pagar(*, conta: ContaPagar, company_id) -> ContaPagar:
    try:
        return (
            ContaPagar.objects.select_for_update(of=("self",))
            .select_related("categoria", "fornecedor")
            .get(pk=conta.pk, company_id=company_id, deleted_at__isnull=True)
        )
    except ContaPagar.DoesNotExist:
        raise NotFound("Conta a pagar não encontrada.")


def _validate_categoria_despesa(categoria: CategoriaFinanceira, company_id) -> None:
    _ensure_same_company(obj=categoria, company_id=company_id, field="categoria")
    if categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
        raise ValidationError({"categoria": "Conta a pagar exige categoria de despesa."})
    if not categoria.ativa or not categoria.is_active:
        raise ValidationError({"categoria": "Categoria financeira inativa."})


@transaction.atomic
def criar_conta_pagar(*, user, data: dict[str, Any], request=None) -> ContaPagar:
    require_company(user)
    fornecedor = data.get("fornecedor")
    categoria = data["categoria"]
    _ensure_same_company(obj=fornecedor, company_id=user.company_id, field="fornecedor")
    _validate_categoria_despesa(categoria, user.company_id)

    conta = ContaPagar(
        company=user.company,
        fornecedor=fornecedor,
        descricao=data["descricao"],
        categoria=categoria,
        valor_total=money(data["valor_total"]),
        valor_pago=ZERO_MONEY,
        valor_restante=money(data["valor_total"]),
        data_emissao=data.get("data_emissao") or timezone.localdate(),
        data_vencimento=data["data_vencimento"],
        observacao=data.get("observacao", ""),
        created_by=user,
    )
    _full_clean_or_400(conta)
    conta.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=conta,
        after=conta_pagar_snapshot(conta),
        request=request,
    )
    return conta


@transaction.atomic
def update_conta_pagar(
    *,
    user,
    conta: ContaPagar,
    data: dict[str, Any],
    request=None,
) -> ContaPagar:
    require_company(user)
    conta = _locked_conta_pagar(conta=conta, company_id=user.company_id)
    if conta.status != ContaPagar.STATUS_ABERTA or conta.valor_pago > ZERO_MONEY:
        raise ValidationError({"status": "Somente conta aberta sem pagamento pode ser alterada."})

    before = conta_pagar_snapshot(conta)
    if "fornecedor" in data:
        _ensure_same_company(obj=data["fornecedor"], company_id=user.company_id, field="fornecedor")
        conta.fornecedor = data["fornecedor"]
    if "categoria" in data:
        _validate_categoria_despesa(data["categoria"], user.company_id)
        conta.categoria = data["categoria"]
    for field in ("descricao", "data_emissao", "data_vencimento", "observacao"):
        if field in data:
            setattr(conta, field, data[field])
    if "valor_total" in data:
        conta.valor_total = money(data["valor_total"])
        conta.valor_restante = money(conta.valor_total - conta.valor_pago)
    _save_conta_pagar(
        conta,
        update_fields=[
            "fornecedor",
            "categoria",
            "descricao",
            "valor_total",
            "valor_restante",
            "data_emissao",
            "data_vencimento",
            "observacao",
        ],
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=conta_pagar_snapshot(conta),
        request=request,
    )
    return conta


@transaction.atomic
def pagar_conta_pagar(
    *,
    user,
    conta: ContaPagar,
    data: dict[str, Any],
    request=None,
) -> ContaPagar:
    require_company(user)
    from .lancamento import criar_lancamento_financeiro, get_or_create_lancamento_idempotente

    conta = _locked_conta_pagar(conta=conta, company_id=user.company_id)
    if conta.status != ContaPagar.STATUS_ABERTA:
        raise ValidationError({"status": "Somente conta aberta pode ser paga."})

    existing = get_or_create_lancamento_idempotente(
        company_id=user.company_id,
        idempotency_key=data.get("idempotency_key", ""),
    )
    if existing:
        return conta

    valor = money(data["valor"])
    if valor <= ZERO_MONEY:
        raise ValidationError({"valor": "Valor deve ser maior que zero."})
    if valor > conta.valor_restante:
        raise ValidationError({"valor": "Pagamento maior que o valor restante."})

    from ..models import ContaFinanceira
    conta_financeira = data["conta_financeira"]
    saldo_atual = (
        ContaFinanceira.objects.filter(pk=conta_financeira.pk)
        .values_list("saldo_atual", flat=True)
        .first()
        or ZERO_MONEY
    )
    if saldo_atual < valor:
        raise ValidationError({
            "conta_financeira": (
                f"Saldo insuficiente na conta financeira. "
                f"Disponível: R$ {saldo_atual:.2f}. "
                f"Necessário: R$ {valor:.2f}."
            )
        })

    before = conta_pagar_snapshot(conta)
    criar_lancamento_financeiro(
        user=user,
        conta_financeira=conta_financeira,
        categoria=conta.categoria,
        tipo=LancamentoFinanceiro.TIPO_SAIDA,
        valor=valor,
        data_lancamento=data.get("data_pagamento") or timezone.now(),
        descricao=data.get("descricao") or f"Pagamento: {conta.descricao}",
        origem_tipo=LancamentoFinanceiro.ORIGEM_CONTA_PAGAR,
        origem_id=conta.pk,
        forma_pagamento=data.get("forma_pagamento", LancamentoFinanceiro.FORMA_OUTRO),
        idempotency_key=data.get("idempotency_key", ""),
        metadata={"conta_pagar_id": str(conta.pk), **(data.get("metadata") or {})},
        request=request,
    )

    conta.valor_pago = money(conta.valor_pago + valor)
    conta.valor_restante = money(conta.valor_total - conta.valor_pago)
    update_fields = ["valor_pago", "valor_restante"]
    if conta.valor_restante == ZERO_MONEY:
        conta.status = ContaPagar.STATUS_PAGA
        conta.data_pagamento = data.get("data_pagamento") or timezone.now()
        update_fields.extend(["status", "data_pagamento"])
    _save_conta_pagar(conta, update_fields=update_fields)
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=conta_pagar_snapshot(conta),
        request=request,
    )
    return conta


@transaction.atomic
def cancelar_conta_pagar(
    *,
    user,
    conta: ContaPagar,
    motivo: str,
    request=None,
) -> ContaPagar:
    require_company(user)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})
    conta = _locked_conta_pagar(conta=conta, company_id=user.company_id)
    if conta.status == ContaPagar.STATUS_CANCELADA:
        raise ValidationError({"status": "Conta a pagar já está cancelada."})
    if conta.valor_pago > ZERO_MONEY:
        raise ValidationError({"valor_pago": "Conta com pagamento não pode ser cancelada na V1."})

    before = conta_pagar_snapshot(conta)
    conta.status = ContaPagar.STATUS_CANCELADA
    conta.cancelled_by = user
    conta.cancelled_at = timezone.now()
    conta.motivo_cancelamento = motivo
    _save_conta_pagar(
        conta,
        update_fields=["status", "cancelled_by", "cancelled_at", "motivo_cancelamento"],
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=conta_pagar_snapshot(conta),
        request=request,
    )
    return conta
