from django.db.models import QuerySet, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound

from .models import Venda, ZERO_MONEY


def get_venda_by_id(*, company_id, venda_id) -> Venda:
    try:
        return (
            Venda.objects.select_related("cliente", "conta_financeira", "created_by", "cancelled_by")
            .get(pk=venda_id, company_id=company_id, deleted_at__isnull=True)
        )
    except Venda.DoesNotExist:
        raise NotFound("Venda não encontrada.")


def search_vendas(*, company_id, filters: dict) -> QuerySet:
    qs = Venda.objects.filter(company_id=company_id, deleted_at__isnull=True)
    qs = qs.select_related("cliente", "conta_financeira", "created_by")

    status = filters.get("status")
    if status:
        qs = qs.filter(status=status)

    forma_pagamento = filters.get("forma_pagamento")
    if forma_pagamento:
        qs = qs.filter(forma_pagamento=forma_pagamento)

    data_inicio = filters.get("data_inicio")
    if data_inicio:
        qs = qs.filter(created_at__date__gte=data_inicio)

    data_fim = filters.get("data_fim")
    if data_fim:
        qs = qs.filter(created_at__date__lte=data_fim)

    search = filters.get("search", "").strip()
    if search:
        qs = qs.filter(numero__icontains=search)

    return qs


def get_dashboard_vendas(*, company_id) -> dict:
    today = timezone.localdate()
    mes_inicio = today.replace(day=1)

    base = Venda.objects.filter(company_id=company_id, deleted_at__isnull=True)

    vendas_hoje = base.filter(created_at__date=today, status=Venda.STATUS_CONCLUIDA)
    vendas_mes = base.filter(created_at__date__gte=mes_inicio, status=Venda.STATUS_CONCLUIDA)

    total_hoje = vendas_hoje.aggregate(total=Sum("valor_total"))["total"] or ZERO_MONEY
    total_mes = vendas_mes.aggregate(total=Sum("valor_total"))["total"] or ZERO_MONEY
    count_hoje = vendas_hoje.count()
    count_mes = vendas_mes.count()

    ticket_medio = (total_mes / count_mes) if count_mes else ZERO_MONEY

    return {
        "total_hoje": total_hoje,
        "count_hoje": count_hoje,
        "total_mes": total_mes,
        "count_mes": count_mes,
        "ticket_medio": ticket_medio,
    }
