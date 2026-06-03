from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, QuerySet, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from .models import (
    CaixaDiario,
    CategoriaFinanceira,
    ContaFinanceira,
    ContaPagar,
    LancamentoFinanceiro,
    ZERO_MONEY,
    money,
)


def _require_company_id(company_id: Any) -> None:
    if company_id is None:
        raise PermissionDenied("Usuário sem empresa associada.")


def _base_qs(model, company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return model.objects.filter(company_id=company_id, deleted_at__isnull=True)


def get_contas_financeiras(*, company_id: Any) -> QuerySet:
    return _base_qs(ContaFinanceira, company_id)


def get_categorias_financeiras(*, company_id: Any) -> QuerySet:
    return _base_qs(CategoriaFinanceira, company_id)


def get_lancamentos(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(LancamentoFinanceiro, company_id)
        .select_related(
            "conta_financeira",
            "categoria",
            "caixa_diario",
            "created_by",
            "cancelled_by",
            "estorno_de",
        )
    )


def get_contas_pagar(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(ContaPagar, company_id)
        .select_related("fornecedor", "categoria", "created_by", "cancelled_by")
    )


def get_caixas(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(CaixaDiario, company_id)
        .select_related("conta_financeira", "aberto_por", "fechado_por")
    )


def _get_by_id(qs: QuerySet, pk, message: str):
    try:
        return qs.get(pk=pk)
    except (qs.model.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound(message)


def get_conta_financeira_by_id(*, company_id: Any, conta_id: uuid.UUID) -> ContaFinanceira:
    return _get_by_id(
        get_contas_financeiras(company_id=company_id),
        conta_id,
        "Conta financeira não encontrada.",
    )


def get_categoria_by_id(*, company_id: Any, categoria_id: uuid.UUID) -> CategoriaFinanceira:
    return _get_by_id(
        get_categorias_financeiras(company_id=company_id),
        categoria_id,
        "Categoria financeira não encontrada.",
    )


def get_lancamento_by_id(*, company_id: Any, lancamento_id: uuid.UUID) -> LancamentoFinanceiro:
    return _get_by_id(
        get_lancamentos(company_id=company_id),
        lancamento_id,
        "Lançamento financeiro não encontrado.",
    )


def get_conta_pagar_by_id(*, company_id: Any, conta_id: uuid.UUID) -> ContaPagar:
    return _get_by_id(
        get_contas_pagar(company_id=company_id),
        conta_id,
        "Conta a pagar não encontrada.",
    )


def get_caixa_by_id(*, company_id: Any, caixa_id: uuid.UUID) -> CaixaDiario:
    return _get_by_id(
        get_caixas(company_id=company_id),
        caixa_id,
        "Caixa diário não encontrado.",
    )


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def search_lancamentos(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = get_lancamentos(company_id=company_id)
    if not filters:
        return qs
    for param, field in (
        ("conta_financeira", "conta_financeira_id"),
        ("categoria", "categoria_id"),
        ("tipo", "tipo"),
        ("status", "status"),
        ("origem_tipo", "origem_tipo"),
        ("forma_pagamento", "forma_pagamento"),
    ):
        if value := filters.get(param):
            qs = qs.filter(**{field: value})
    if date_after := filters.get("data_lancamento_after"):
        qs = qs.filter(data_lancamento__date__gte=date_after)
    if date_before := filters.get("data_lancamento_before"):
        qs = qs.filter(data_lancamento__date__lte=date_before)
    if (gte := filters.get("valor_gte")) is not None:
        value = _decimal(gte)
        if value is not None:
            qs = qs.filter(valor__gte=value)
    if (lte := filters.get("valor_lte")) is not None:
        value = _decimal(lte)
        if value is not None:
            qs = qs.filter(valor__lte=value)
    if q := filters.get("search"):
        qs = qs.filter(
            Q(descricao__icontains=q)
            | Q(conta_financeira__nome__icontains=q)
            | Q(categoria__nome__icontains=q)
            | Q(idempotency_key__icontains=q)
        )
    return qs


def search_contas_pagar(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = get_contas_pagar(company_id=company_id)
    if not filters:
        return qs
    for param, field in (
        ("fornecedor", "fornecedor_id"),
        ("categoria", "categoria_id"),
        ("status", "status"),
    ):
        if value := filters.get(param):
            qs = qs.filter(**{field: value})
    if situacao := filters.get("situacao"):
        situacao = situacao.lower()
        if situacao == "parcial":
            qs = qs.filter(
                status=ContaPagar.STATUS_ABERTA,
                valor_pago__gt=ZERO_MONEY,
                valor_restante__gt=ZERO_MONEY,
            )
        elif situacao == "atrasada":
            qs = qs.filter(
                status=ContaPagar.STATUS_ABERTA,
                data_vencimento__lt=timezone.localdate(),
                valor_restante__gt=ZERO_MONEY,
            )
    if date_before := filters.get("data_vencimento_before"):
        qs = qs.filter(data_vencimento__lte=date_before)
    if date_after := filters.get("data_vencimento_after"):
        qs = qs.filter(data_vencimento__gte=date_after)
    if (gte := filters.get("valor_restante_gte")) is not None:
        value = _decimal(gte)
        if value is not None:
            qs = qs.filter(valor_restante__gte=value)
    if (lte := filters.get("valor_restante_lte")) is not None:
        value = _decimal(lte)
        if value is not None:
            qs = qs.filter(valor_restante__lte=value)
    if q := filters.get("search"):
        qs = qs.filter(
            Q(descricao__icontains=q)
            | Q(observacao__icontains=q)
            | Q(fornecedor__razao_social__icontains=q)
            | Q(fornecedor__nome_fantasia__icontains=q)
            | Q(categoria__nome__icontains=q)
        )
    return qs


def search_caixas(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = get_caixas(company_id=company_id)
    if not filters:
        return qs
    if data := filters.get("data"):
        qs = qs.filter(data=data)
    if status := filters.get("status"):
        qs = qs.filter(status=status)
    if conta := filters.get("conta_financeira"):
        qs = qs.filter(conta_financeira_id=conta)
    return qs


def _sum_money(qs: QuerySet, field: str = "valor") -> Decimal:
    return money(qs.aggregate(total=Sum(field))["total"] or ZERO_MONEY)


def get_dashboard_financeiro(*, company_id: Any) -> dict[str, Any]:
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)
    inicio_ano = hoje.replace(month=1, day=1)

    lancamentos = get_lancamentos(company_id=company_id).filter(
        status=LancamentoFinanceiro.STATUS_CONFIRMADO,
    )
    entradas = lancamentos.filter(tipo=LancamentoFinanceiro.TIPO_ENTRADA)
    saidas = lancamentos.filter(tipo=LancamentoFinanceiro.TIPO_SAIDA)
    contas_pagar = get_contas_pagar(company_id=company_id)

    fluxo_diario = list(
        lancamentos.annotate(dia=TruncDate("data_lancamento"))
        .values("dia", "tipo")
        .annotate(total=Sum("valor"))
        .order_by("dia", "tipo")
    )
    por_categoria = (
        lancamentos.values("tipo", "categoria__nome")
        .annotate(total=Sum("valor"))
        .order_by("categoria__nome")
    )
    from apps.cobrancas.selectors import recuperacao_inadimplencia

    recuperacao = recuperacao_inadimplencia(company_id)

    return {
        "recebido_hoje": _sum_money(entradas.filter(data_lancamento__date=hoje)),
        "recebido_mes": _sum_money(entradas.filter(data_lancamento__date__gte=inicio_mes)),
        "recebido_ano": _sum_money(entradas.filter(data_lancamento__date__gte=inicio_ano)),
        "total_contas_pagar_abertas": _sum_money(
            contas_pagar.filter(status=ContaPagar.STATUS_ABERTA),
            field="valor_restante",
        ),
        "total_contas_pagar_vencidas": _sum_money(
            contas_pagar.filter(
                status=ContaPagar.STATUS_ABERTA,
                data_vencimento__lt=hoje,
            ),
            field="valor_restante",
        ),
        "saldo_caixa": _sum_money(
            get_contas_financeiras(company_id=company_id).filter(
                tipo=ContaFinanceira.TIPO_CAIXA,
                ativo=True,
            ),
            field="saldo_atual",
        ),
        "saldo_bancario": _sum_money(
            get_contas_financeiras(company_id=company_id).filter(
                tipo=ContaFinanceira.TIPO_BANCO,
                ativo=True,
            ),
            field="saldo_atual",
        ),
        "saldo_total_financeiro": _sum_money(
            get_contas_financeiras(company_id=company_id).filter(ativo=True),
            field="saldo_atual",
        ),
        "inadimplencia_valor_cobrado": recuperacao["valor_cobrado"],
        "inadimplencia_valor_recuperado": recuperacao["valor_recuperado"],
        "inadimplencia_percentual_recuperacao": recuperacao["percentual_recuperacao"],
        "fluxo_diario": [
            {
                "data": item["dia"].isoformat(),
                "tipo": item["tipo"],
                "total": money(item["total"]),
            }
            for item in fluxo_diario
        ],
        "entradas_por_categoria": [
            {"categoria": item["categoria__nome"], "total": money(item["total"])}
            for item in por_categoria
            if item["tipo"] == LancamentoFinanceiro.TIPO_ENTRADA
        ],
        "saidas_por_categoria": [
            {"categoria": item["categoria__nome"], "total": money(item["total"])}
            for item in por_categoria
            if item["tipo"] == LancamentoFinanceiro.TIPO_SAIDA
        ],
    }
