from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import (
    CategoriaFinanceira,
    ContaFinanceira,
    LancamentoFinanceiro,
    ZERO_MONEY,
    money,
)
from .categoria import _ensure_same_company, _full_clean_or_400, get_categoria_padrao


def conta_snapshot(conta: ContaFinanceira) -> dict[str, Any]:
    return {
        "id": str(conta.pk),
        "company_id": str(conta.company_id),
        "nome": conta.nome,
        "tipo": conta.tipo,
        "saldo_atual": str(conta.saldo_atual),
        "ativo": conta.ativo,
        "observacao": conta.observacao,
        "is_active": conta.is_active,
    }


def _save_conta(conta: ContaFinanceira, *, update_fields: list[str]) -> None:
    try:
        conta.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))
    conta._allow_saldo_update = True
    conta.save(update_fields=[*update_fields, "updated_at"])
    conta._allow_saldo_update = False


@transaction.atomic
def criar_conta_financeira(*, user, data: dict[str, Any], request=None) -> ContaFinanceira:
    require_company(user)
    conta = ContaFinanceira(
        company=user.company,
        nome=data["nome"],
        tipo=data["tipo"],
        saldo_atual=ZERO_MONEY,
        ativo=data.get("ativo", True),
        observacao=data.get("observacao", ""),
    )
    _full_clean_or_400(conta)
    conta.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=conta,
        after=conta_snapshot(conta),
        request=request,
    )
    return conta


@transaction.atomic
def update_conta_financeira(
    *,
    user,
    conta: ContaFinanceira,
    data: dict[str, Any],
    request=None,
) -> ContaFinanceira:
    require_company(user)
    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta_financeira")
    conta = ContaFinanceira.objects.select_for_update().get(
        pk=conta.pk,
        company_id=user.company_id,
        deleted_at__isnull=True,
    )
    before = conta_snapshot(conta)
    for field in ("nome", "tipo", "ativo", "observacao"):
        if field in data:
            setattr(conta, field, data[field])
    _save_conta(conta, update_fields=["nome", "tipo", "ativo", "observacao"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=conta_snapshot(conta),
        request=request,
    )
    return conta


@transaction.atomic
def inativar_conta_financeira(
    *,
    user,
    conta: ContaFinanceira,
    request=None,
) -> ContaFinanceira:
    require_company(user)
    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta_financeira")
    conta = ContaFinanceira.objects.select_for_update().get(
        pk=conta.pk,
        company_id=user.company_id,
        deleted_at__isnull=True,
    )
    if money(conta.saldo_atual) != ZERO_MONEY:
        raise ValidationError({"saldo_atual": "Conta com saldo não pode ser inativada."})
    if LancamentoFinanceiro.objects.filter(
        company_id=user.company_id,
        conta_financeira=conta,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({"conta_financeira": "Conta com lançamentos não pode ser inativada."})

    before = conta_snapshot(conta)
    conta.ativo = False
    conta.is_active = False
    _save_conta(conta, update_fields=["ativo", "is_active"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=before,
        after=conta_snapshot(conta),
        request=request,
    )
    return conta


def _categoria_ajuste(*, user, tipo: str, categoria: CategoriaFinanceira | None):
    if categoria is not None:
        _ensure_same_company(obj=categoria, company_id=user.company_id, field="categoria")
        return categoria
    nome = "Outros" if tipo == LancamentoFinanceiro.TIPO_ENTRADA else "Outros"
    categoria_tipo = (
        CategoriaFinanceira.TIPO_RECEITA
        if tipo == LancamentoFinanceiro.TIPO_ENTRADA
        else CategoriaFinanceira.TIPO_DESPESA
    )
    return get_categoria_padrao(company=user.company, nome=nome, tipo=categoria_tipo)


@transaction.atomic
def ajustar_saldo_conta(
    *,
    user,
    conta: ContaFinanceira,
    data: dict[str, Any],
    request=None,
) -> LancamentoFinanceiro:
    require_company(user)
    from .lancamento import criar_lancamento_financeiro

    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta_financeira")
    tipo = data["tipo"]
    categoria = _categoria_ajuste(user=user, tipo=tipo, categoria=data.get("categoria"))
    return criar_lancamento_financeiro(
        user=user,
        conta_financeira=conta,
        categoria=categoria,
        tipo=tipo,
        valor=data["valor"],
        data_lancamento=data.get("data_lancamento"),
        descricao=data.get("descricao", "Ajuste de saldo"),
        origem_tipo=LancamentoFinanceiro.ORIGEM_AJUSTE,
        origem_id=conta.pk,
        forma_pagamento=data.get("forma_pagamento", LancamentoFinanceiro.FORMA_OUTRO),
        idempotency_key=data.get("idempotency_key", ""),
        metadata=data.get("metadata") or {},
        request=request,
    )
