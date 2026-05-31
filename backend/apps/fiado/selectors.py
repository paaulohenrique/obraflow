from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Avg, Count, Q, QuerySet, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.clientes.models import Cliente

from .models import ContaFiado, HistoricoFiado, ItemFiado, PagamentoFiado, ZERO_MONEY, money


def _require_company_id(company_id: Any) -> None:
    if company_id is None:
        raise PermissionDenied("Usuário sem empresa associada.")


def _base_qs(model, company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return model.objects.filter(company_id=company_id, deleted_at__isnull=True)


def get_contas(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(ContaFiado, company_id)
        .select_related("cliente", "created_by", "closed_by", "cancelled_by")
    )


def get_itens(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(ItemFiado, company_id)
        .select_related(
            "conta",
            "produto",
            "created_by",
            "cancelled_by",
            "movimentacao_estoque",
            "movimentacao_cancelamento",
        )
    )


def get_pagamentos(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(PagamentoFiado, company_id)
        .select_related("conta", "created_by", "cancelled_by")
    )


def get_historicos(*, company_id: Any) -> QuerySet:
    return (
        _base_qs(HistoricoFiado, company_id)
        .select_related("conta", "item", "pagamento", "created_by")
    )


def get_conta_by_id(*, company_id: Any, conta_id: uuid.UUID) -> ContaFiado:
    try:
        return get_contas(company_id=company_id).get(pk=conta_id)
    except (ContaFiado.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Conta fiado não encontrada.")


def get_item_by_id(*, company_id: Any, item_id: uuid.UUID) -> ItemFiado:
    try:
        return get_itens(company_id=company_id).get(pk=item_id)
    except (ItemFiado.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Item fiado não encontrado.")


def get_pagamento_by_id(*, company_id: Any, pagamento_id: uuid.UUID) -> PagamentoFiado:
    try:
        return get_pagamentos(company_id=company_id).get(pk=pagamento_id)
    except (PagamentoFiado.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Pagamento fiado não encontrado.")


def get_itens_da_conta(*, company_id: Any, conta_id: uuid.UUID) -> QuerySet:
    get_conta_by_id(company_id=company_id, conta_id=conta_id)
    return get_itens(company_id=company_id).filter(conta_id=conta_id).order_by("-data_lancamento")


def get_pagamentos_da_conta(*, company_id: Any, conta_id: uuid.UUID) -> QuerySet:
    get_conta_by_id(company_id=company_id, conta_id=conta_id)
    return (
        get_pagamentos(company_id=company_id)
        .filter(conta_id=conta_id)
        .order_by("-data_pagamento", "-created_at")
    )


def get_historico_da_conta(*, company_id: Any, conta_id: uuid.UUID) -> QuerySet:
    get_conta_by_id(company_id=company_id, conta_id=conta_id)
    return get_historicos(company_id=company_id).filter(conta_id=conta_id).order_by("created_at")


def get_contas_abertas(*, company_id: Any) -> QuerySet:
    return get_contas(company_id=company_id).filter(status=ContaFiado.STATUS_ABERTA)


def get_contas_atrasadas(*, company_id: Any) -> QuerySet:
    return get_contas_abertas(company_id=company_id).filter(
        data_vencimento__lt=timezone.localdate(),
        valor_restante__gt=ZERO_MONEY,
    )


def get_contas_por_cliente(*, company_id: Any, cliente_id: uuid.UUID) -> QuerySet:
    return get_contas(company_id=company_id).filter(cliente_id=cliente_id)


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def search_contas(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = get_contas(company_id=company_id)
    if not filters:
        return qs

    if cliente := filters.get("cliente"):
        qs = qs.filter(cliente_id=cliente)
    if status := filters.get("status"):
        qs = qs.filter(status=status)
    if created_by := filters.get("created_by"):
        qs = qs.filter(created_by_id=created_by)

    if situacao := filters.get("situacao"):
        situacao = situacao.lower()
        if situacao == "parcial":
            qs = qs.filter(
                status=ContaFiado.STATUS_ABERTA,
                valor_pago__gt=ZERO_MONEY,
                valor_restante__gt=ZERO_MONEY,
            )
        elif situacao == "atrasada":
            qs = qs.filter(
                status=ContaFiado.STATUS_ABERTA,
                data_vencimento__lt=timezone.localdate(),
                valor_restante__gt=ZERO_MONEY,
            )

    if data_vencimento_before := filters.get("data_vencimento_before"):
        qs = qs.filter(data_vencimento__lte=data_vencimento_before)
    if data_vencimento_after := filters.get("data_vencimento_after"):
        qs = qs.filter(data_vencimento__gte=data_vencimento_after)

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
            Q(cliente__nome__icontains=q)
            | Q(cliente__cpf_cnpj__icontains=q)
            | Q(observacao__icontains=q)
        )

    return qs


def get_dashboard_fiado(*, company_id: Any) -> dict[str, Any]:
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    contas = get_contas(company_id=company_id)
    contas_abertas = contas.filter(status=ContaFiado.STATUS_ABERTA)
    contas_atrasadas = contas_abertas.filter(
        data_vencimento__lt=hoje,
        valor_restante__gt=ZERO_MONEY,
    )
    pagamentos_confirmados = get_pagamentos(company_id=company_id).filter(
        status=PagamentoFiado.STATUS_CONFIRMADO,
    )

    total_em_aberto = contas_abertas.aggregate(total=Sum("valor_restante"))["total"] or ZERO_MONEY
    total_atrasado = contas_atrasadas.aggregate(total=Sum("valor_restante"))["total"] or ZERO_MONEY
    total_recebido_hoje = (
        pagamentos_confirmados.filter(data_pagamento__date=hoje).aggregate(total=Sum("valor"))[
            "total"
        ]
        or ZERO_MONEY
    )
    total_recebido_mes = (
        pagamentos_confirmados.filter(data_pagamento__date__gte=inicio_mes).aggregate(
            total=Sum("valor")
        )["total"]
        or ZERO_MONEY
    )
    ticket_medio = (
        contas.exclude(status=ContaFiado.STATUS_CANCELADA)
        .filter(valor_total__gt=ZERO_MONEY)
        .aggregate(media=Avg("valor_total"))["media"]
        or ZERO_MONEY
    )

    clientes_devedores = (
        Cliente.objects.filter(
            company_id=company_id,
            deleted_at__isnull=True,
            saldo_devedor__gt=ZERO_MONEY,
        )
        .aggregate(total=Count("id"))["total"]
        or 0
    )

    return {
        "total_em_aberto": money(total_em_aberto),
        "total_atrasado": money(total_atrasado),
        "total_recebido_hoje": money(total_recebido_hoje),
        "total_recebido_mes": money(total_recebido_mes),
        "contas_abertas": contas_abertas.count(),
        "contas_atrasadas": contas_atrasadas.count(),
        "clientes_devedores": clientes_devedores,
        "ticket_medio_fiado": money(ticket_medio),
    }
