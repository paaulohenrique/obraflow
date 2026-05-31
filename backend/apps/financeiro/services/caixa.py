from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import CaixaDiario, ContaFinanceira, LancamentoFinanceiro, ZERO_MONEY, money
from .categoria import _ensure_same_company, _full_clean_or_400


def caixa_snapshot(caixa: CaixaDiario) -> dict[str, Any]:
    return {
        "id": str(caixa.pk),
        "company_id": str(caixa.company_id),
        "conta_financeira_id": str(caixa.conta_financeira_id),
        "data": caixa.data.isoformat(),
        "status": caixa.status,
        "saldo_inicial": str(caixa.saldo_inicial),
        "total_entradas": str(caixa.total_entradas),
        "total_saidas": str(caixa.total_saidas),
        "saldo_final": str(caixa.saldo_final),
        "aberto_por_id": str(caixa.aberto_por_id) if caixa.aberto_por_id else None,
        "fechado_por_id": str(caixa.fechado_por_id) if caixa.fechado_por_id else None,
        "aberto_em": caixa.aberto_em.isoformat() if caixa.aberto_em else None,
        "fechado_em": caixa.fechado_em.isoformat() if caixa.fechado_em else None,
        "observacao": caixa.observacao,
    }


def _save_caixa(caixa: CaixaDiario, *, update_fields: list[str]) -> None:
    try:
        caixa.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))
    caixa.save(update_fields=[*update_fields, "updated_at"])


def get_caixa_aberto(
    *,
    company_id,
    conta_financeira: ContaFinanceira | None = None,
    lock: bool = False,
) -> CaixaDiario | None:
    qs = CaixaDiario.objects.filter(
        company_id=company_id,
        status=CaixaDiario.STATUS_ABERTO,
        deleted_at__isnull=True,
    )
    if conta_financeira is not None:
        qs = qs.filter(conta_financeira=conta_financeira)
    if lock:
        qs = qs.select_for_update(of=("self",))
    return qs.select_related("conta_financeira", "aberto_por", "fechado_por").first()


def _locked_caixa(*, caixa: CaixaDiario, company_id) -> CaixaDiario:
    try:
        return (
            CaixaDiario.objects.select_for_update(of=("self",))
            .select_related("conta_financeira", "aberto_por", "fechado_por")
            .get(pk=caixa.pk, company_id=company_id, deleted_at__isnull=True)
        )
    except CaixaDiario.DoesNotExist:
        raise NotFound("Caixa diário não encontrado.")


def recalcular_totais_caixa(caixa: CaixaDiario) -> CaixaDiario:
    totais = (
        LancamentoFinanceiro.objects.filter(
            company_id=caixa.company_id,
            caixa_diario=caixa,
            deleted_at__isnull=True,
        )
        .values("tipo")
        .annotate(total=Sum("valor"))
    )
    entradas = ZERO_MONEY
    saidas = ZERO_MONEY
    for item in totais:
        if item["tipo"] == LancamentoFinanceiro.TIPO_ENTRADA:
            entradas = money(item["total"])
        elif item["tipo"] == LancamentoFinanceiro.TIPO_SAIDA:
            saidas = money(item["total"])
    caixa.total_entradas = entradas
    caixa.total_saidas = saidas
    caixa.saldo_final = money(caixa.saldo_inicial + entradas - saidas)
    return caixa


@transaction.atomic
def abrir_caixa(*, user, data: dict[str, Any], request=None) -> CaixaDiario:
    require_company(user)
    conta = data["conta_financeira"]
    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta_financeira")
    conta = ContaFinanceira.objects.select_for_update().get(
        pk=conta.pk,
        company_id=user.company_id,
        deleted_at__isnull=True,
    )
    if conta.tipo != ContaFinanceira.TIPO_CAIXA:
        raise ValidationError({"conta_financeira": "Caixa diário exige conta tipo CAIXA."})
    if not conta.ativo or not conta.is_active:
        raise ValidationError({"conta_financeira": "Conta financeira inativa."})

    data_caixa = data.get("data") or timezone.localdate()
    if CaixaDiario.objects.select_for_update().filter(
        company_id=user.company_id,
        data=data_caixa,
        status=CaixaDiario.STATUS_ABERTO,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({"data": "Já existe caixa aberto para esta empresa nesta data."})

    caixa = CaixaDiario(
        company=user.company,
        conta_financeira=conta,
        data=data_caixa,
        saldo_inicial=money(conta.saldo_atual),
        saldo_final=money(conta.saldo_atual),
        aberto_por=user,
        aberto_em=timezone.now(),
        observacao=data.get("observacao", ""),
    )
    _full_clean_or_400(caixa)
    caixa.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=caixa,
        after=caixa_snapshot(caixa),
        request=request,
    )
    return caixa


@transaction.atomic
def fechar_caixa(*, user, caixa: CaixaDiario, data: dict[str, Any] | None = None, request=None):
    require_company(user)
    _ensure_same_company(obj=caixa, company_id=user.company_id, field="caixa")
    caixa = _locked_caixa(caixa=caixa, company_id=user.company_id)
    if caixa.status != CaixaDiario.STATUS_ABERTO:
        raise ValidationError({"status": "Somente caixa aberto pode ser fechado."})

    before = caixa_snapshot(caixa)
    recalcular_totais_caixa(caixa)
    caixa.status = CaixaDiario.STATUS_FECHADO
    caixa.fechado_por = user
    caixa.fechado_em = timezone.now()
    if data and "observacao" in data:
        caixa.observacao = data.get("observacao") or ""
    _save_caixa(
        caixa,
        update_fields=[
            "status",
            "total_entradas",
            "total_saidas",
            "saldo_final",
            "fechado_por",
            "fechado_em",
            "observacao",
        ],
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=caixa,
        before=before,
        after=caixa_snapshot(caixa),
        request=request,
    )
    return caixa


@transaction.atomic
def reabrir_caixa(*, user, caixa: CaixaDiario, data: dict[str, Any] | None = None, request=None):
    require_company(user)
    if getattr(user, "role", "") != "admin":
        raise PermissionDenied("Apenas administradores podem reabrir caixa.")
    _ensure_same_company(obj=caixa, company_id=user.company_id, field="caixa")
    caixa = _locked_caixa(caixa=caixa, company_id=user.company_id)
    if caixa.status != CaixaDiario.STATUS_FECHADO:
        raise ValidationError({"status": "Somente caixa fechado pode ser reaberto."})
    if CaixaDiario.objects.select_for_update().filter(
        company_id=user.company_id,
        data=caixa.data,
        status=CaixaDiario.STATUS_ABERTO,
        deleted_at__isnull=True,
    ).exclude(pk=caixa.pk).exists():
        raise ValidationError({"data": "Já existe outro caixa aberto nesta data."})

    before = caixa_snapshot(caixa)
    caixa.status = CaixaDiario.STATUS_ABERTO
    caixa.fechado_por = None
    caixa.fechado_em = None
    if data and "observacao" in data:
        caixa.observacao = data.get("observacao") or caixa.observacao
    _save_caixa(caixa, update_fields=["status", "fechado_por", "fechado_em", "observacao"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=caixa,
        before=before,
        after=caixa_snapshot(caixa),
        request=request,
    )
    return caixa
