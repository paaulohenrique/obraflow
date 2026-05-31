from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Avg, Q, QuerySet, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from .models import BoletoOCR, HistoricoBoleto


def _require_company_id(company_id: Any) -> None:
    if company_id is None:
        raise PermissionDenied("Usuário sem empresa associada.")


def _base_boleto_qs(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        BoletoOCR.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("fornecedor", "conta_pagar", "created_by", "confirmado_por", "rejeitado_por")
    )


def get_boletos_visiveis(*, user) -> QuerySet:
    qs = _base_boleto_qs(getattr(user, "company_id", None))
    if getattr(user, "role", "") == "seller":
        qs = qs.filter(created_by=user)
    return qs


def get_boleto_by_id(*, user, boleto_id) -> BoletoOCR:
    try:
        return get_boletos_visiveis(user=user).get(pk=boleto_id)
    except (BoletoOCR.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Boleto não encontrado.")


def get_historico(*, user, boleto_id) -> QuerySet:
    boleto = get_boleto_by_id(user=user, boleto_id=boleto_id)
    return (
        HistoricoBoleto.objects.filter(company_id=boleto.company_id, boleto=boleto, deleted_at__isnull=True)
        .select_related("created_by")
        .order_by("-created_at")
    )


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def search_boletos(*, user, filters: dict | None = None) -> QuerySet:
    qs = get_boletos_visiveis(user=user)
    if not filters:
        return qs
    for param, field in (
        ("status", "status"),
        ("tipo_arquivo", "tipo_arquivo"),
        ("fornecedor", "fornecedor_id"),
        ("conta_pagar", "conta_pagar_id"),
    ):
        if value := filters.get(param):
            qs = qs.filter(**{field: value})
    if date_after := filters.get("vencimento_after"):
        qs = qs.filter(vencimento__gte=date_after)
    if date_before := filters.get("vencimento_before"):
        qs = qs.filter(vencimento__lte=date_before)
    if created_after := filters.get("created_at_after"):
        qs = qs.filter(created_at__date__gte=created_after)
    if created_before := filters.get("created_at_before"):
        qs = qs.filter(created_at__date__lte=created_before)
    if (gte := filters.get("valor_gte")) is not None:
        value = _decimal(gte)
        if value is not None:
            qs = qs.filter(valor__gte=value)
    if (lte := filters.get("valor_lte")) is not None:
        value = _decimal(lte)
        if value is not None:
            qs = qs.filter(valor__lte=value)
    if (conf := filters.get("confianca_lte")) is not None:
        value = _decimal(conf)
        if value is not None:
            qs = qs.filter(confianca_ocr__lte=value)
    if q := filters.get("search"):
        qs = qs.filter(
            Q(fornecedor_nome__icontains=q)
            | Q(banco_nome__icontains=q)
            | Q(linha_digitavel__icontains=q)
            | Q(codigo_barras__icontains=q)
            | Q(arquivo_nome_original__icontains=q)
        )
    return qs


def get_dashboard_boletos(*, user) -> dict[str, Any]:
    qs = get_boletos_visiveis(user=user)
    today = timezone.localdate()
    processados = qs.filter(ocr_finished_at__date=today)
    sucesso = qs.filter(status__in=[BoletoOCR.STATUS_AGUARDANDO_REVISAO, BoletoOCR.STATUS_CONFIRMADO])
    total_processados = qs.exclude(ocr_finished_at__isnull=True).count()
    sucesso_count = sucesso.count()
    taxa = Decimal("0.00") if total_processados == 0 else Decimal(sucesso_count * 100) / Decimal(total_processados)
    return {
        "boletos_enviados_hoje": qs.filter(created_at__date=today).count(),
        "boletos_processados_hoje": processados.count(),
        "pendentes_revisao": qs.filter(status=BoletoOCR.STATUS_AGUARDANDO_REVISAO).count(),
        "ocrs_com_erro": qs.filter(status=BoletoOCR.STATUS_ERRO).count(),
        "contas_pagar_geradas": qs.filter(conta_pagar__isnull=False).count(),
        "valor_total_identificado": qs.exclude(valor__isnull=True).aggregate(total=Sum("valor"))["total"] or Decimal("0.00"),
        "valor_total_confirmado": qs.filter(status=BoletoOCR.STATUS_CONFIRMADO).aggregate(total=Sum("valor"))["total"] or Decimal("0.00"),
        "taxa_sucesso_ocr": taxa.quantize(Decimal("0.01")),
        "confianca_media": (qs.aggregate(avg=Avg("confianca_ocr"))["avg"] or Decimal("0.00")).quantize(Decimal("0.01")),
        "vencimentos_7_dias": qs.filter(
            status=BoletoOCR.STATUS_CONFIRMADO,
            vencimento__gte=today,
            vencimento__lte=today + timedelta(days=7),
        ).count(),
        "vencimentos_30_dias": qs.filter(
            status=BoletoOCR.STATUS_CONFIRMADO,
            vencimento__gte=today,
            vencimento__lte=today + timedelta(days=30),
        ).count(),
    }
