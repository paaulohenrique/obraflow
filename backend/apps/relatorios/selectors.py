from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    Min,
    Q,
    QuerySet,
    Sum,
)
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import PermissionDenied

from apps.boletos.models import BoletoOCR
from apps.clientes.models import Cliente
from apps.estoque.models import MovimentacaoEstoque, Produto
from apps.fiado.models import ContaFiado, PagamentoFiado
from apps.financeiro.models import ContaFinanceira, ContaPagar, LancamentoFinanceiro
from apps.vendas.models import ItemVenda, Venda


ZERO_MONEY = Decimal("0.00")


def money(value: Decimal | None) -> Decimal:
    return (value or ZERO_MONEY).quantize(Decimal("0.01"))


def _require_company_id(company_id: Any) -> None:
    if company_id is None:
        raise PermissionDenied("Usuário sem empresa associada.")


def _date_param(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return parse_date(value)
    return None


def _period(filters: dict[str, Any] | None) -> tuple[date | None, date | None]:
    filters = filters or {}
    start = _date_param(filters.get("data_inicio") or filters.get("periodo_inicio"))
    end = _date_param(filters.get("data_fim") or filters.get("periodo_fim"))
    if start and end and start > end:
        start, end = end, start
    return start, end


def _sum_money(qs: QuerySet, field: str = "valor") -> Decimal:
    return money(qs.aggregate(total=Sum(field))["total"] or ZERO_MONEY)


def _filter_datetime_period(
    qs: QuerySet,
    field: str,
    start: date | None,
    end: date | None,
) -> QuerySet:
    if start:
        qs = qs.filter(**{f"{field}__date__gte": start})
    if end:
        qs = qs.filter(**{f"{field}__date__lte": end})
    return qs


def _filter_date_period(
    qs: QuerySet,
    field: str,
    start: date | None,
    end: date | None,
) -> QuerySet:
    if start:
        qs = qs.filter(**{f"{field}__gte": start})
    if end:
        qs = qs.filter(**{f"{field}__lte": end})
    return qs


def _contas_fiado_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        ContaFiado.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("cliente", "created_by", "closed_by", "cancelled_by")
    )


def _pagamentos_fiado_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        PagamentoFiado.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("conta", "conta__cliente")
    )


def _vendas_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        Venda.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("cliente", "conta_financeira", "created_by")
    )


def _itens_venda_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        ItemVenda.objects.filter(
            company_id=company_id,
            deleted_at__isnull=True,
            venda__deleted_at__isnull=True,
        )
        .select_related("venda", "produto", "produto__categoria", "produto__unidade")
    )


def _lancamentos_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        LancamentoFinanceiro.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("conta_financeira", "categoria", "created_by")
    )


def _contas_pagar_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        ContaPagar.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("fornecedor", "categoria", "created_by")
    )


def _produtos_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        Produto.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("categoria", "fornecedor_principal", "unidade")
    )


def _movimentacoes_base(company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return (
        MovimentacaoEstoque.objects.filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("produto", "fornecedor")
    )


def _lucro_bruto_estimado(company_id: Any, start: date | None, end: date | None) -> Decimal:
    itens = _itens_venda_base(company_id).filter(venda__status=Venda.STATUS_CONCLUIDA)
    itens = _filter_datetime_period(itens, "venda__created_at", start, end)
    custo_expr = ExpressionWrapper(
        F("quantidade") * F("produto__custo_medio"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    totais = itens.aggregate(receita=Sum("subtotal"), custo=Sum(custo_expr))
    return money((totais["receita"] or ZERO_MONEY) - (totais["custo"] or ZERO_MONEY))


def get_dashboard_executivo(*, company_id: Any) -> dict[str, Any]:
    _require_company_id(company_id)
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    lancamentos_caixa = _lancamentos_base(company_id).filter(
        status=LancamentoFinanceiro.STATUS_CONFIRMADO,
        conta_financeira__tipo=ContaFinanceira.TIPO_CAIXA,
    )
    caixa = lancamentos_caixa.aggregate(
        entradas=Sum("valor", filter=Q(tipo=LancamentoFinanceiro.TIPO_ENTRADA)),
        saidas=Sum("valor", filter=Q(tipo=LancamentoFinanceiro.TIPO_SAIDA)),
    )
    caixa_entradas = money(caixa["entradas"])
    caixa_saidas = money(caixa["saidas"])

    contas_fiado_abertas = _contas_fiado_base(company_id).filter(
        status=ContaFiado.STATUS_ABERTA,
        valor_restante__gt=ZERO_MONEY,
    )
    fiado_em_aberto = _sum_money(contas_fiado_abertas, "valor_restante")
    fiado_vencido = _sum_money(
        contas_fiado_abertas.filter(data_vencimento__lt=hoje),
        "valor_restante",
    )

    contas_pagar_abertas = _contas_pagar_base(company_id).filter(
        status=ContaPagar.STATUS_ABERTA,
        valor_restante__gt=ZERO_MONEY,
    )
    boletos_confirmados_abertos = BoletoOCR.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        status=BoletoOCR.STATUS_CONFIRMADO,
        conta_pagar__status=ContaPagar.STATUS_ABERTA,
        conta_pagar__deleted_at__isnull=True,
        conta_pagar__valor_restante__gt=ZERO_MONEY,
    )
    contas_sem_boleto = contas_pagar_abertas.filter(boleto_ocr__isnull=True)
    boletos_confirmados_valor = money(
        boletos_confirmados_abertos.aggregate(total=Sum("conta_pagar__valor_restante"))["total"]
    )
    contas_abertas_valor = _sum_money(contas_sem_boleto, "valor_restante")

    vendas_mes = _sum_money(
        _vendas_base(company_id).filter(
            status=Venda.STATUS_CONCLUIDA,
            created_at__date__gte=inicio_mes,
        ),
        "valor_total",
    )
    clientes_inadimplentes = Cliente.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        saldo_devedor__gt=ZERO_MONEY,
    ).count()
    produtos_criticos = _produtos_base(company_id).filter(
        is_active=True,
        estoque_atual__lte=F("estoque_minimo"),
    ).count()

    recebimentos_pendentes = ZERO_MONEY

    return {
        "caixa_atual": money(caixa_entradas - caixa_saidas),
        "caixa_entradas": caixa_entradas,
        "caixa_saidas": caixa_saidas,
        "a_receber": money(fiado_em_aberto + recebimentos_pendentes),
        "fiados_em_aberto_componente": fiado_em_aberto,
        "recebimentos_pendentes": recebimentos_pendentes,
        "a_pagar": money(contas_abertas_valor + boletos_confirmados_valor),
        "contas_abertas": contas_abertas_valor,
        "boletos_confirmados": boletos_confirmados_valor,
        "fiado_em_aberto": fiado_em_aberto,
        "fiado_vencido": fiado_vencido,
        "vendas_mes": vendas_mes,
        "clientes_inadimplentes": clientes_inadimplentes,
        "produtos_estoque_critico": produtos_criticos,
        "atualizado_em": timezone.now(),
    }


def get_relatorio_fiado(*, company_id: Any, filters: dict[str, Any] | None = None):
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)
    start, end = _period(filters)

    contas = _contas_fiado_base(company_id)
    contas = _filter_datetime_period(contas, "data_abertura", start, end)
    if cliente := (filters or {}).get("cliente"):
        contas = contas.filter(cliente_id=cliente)
    if status := (filters or {}).get("status"):
        contas = contas.filter(status=status)

    contas_abertas = contas.filter(
        status=ContaFiado.STATUS_ABERTA,
        valor_restante__gt=ZERO_MONEY,
    )
    contas_vencidas = contas_abertas.filter(data_vencimento__lt=hoje)

    pagamentos_mes = _pagamentos_fiado_base(company_id).filter(
        status=PagamentoFiado.STATUS_CONFIRMADO,
        data_pagamento__date__gte=inicio_mes,
    )
    if cliente := (filters or {}).get("cliente"):
        pagamentos_mes = pagamentos_mes.filter(conta__cliente_id=cliente)

    ranking_raw = (
        contas_abertas.values("cliente_id", "cliente__nome")
        .annotate(
            saldo=Sum("valor_restante"),
            vencimento_mais_antigo=Min(
                "data_vencimento",
                filter=Q(data_vencimento__lt=hoje),
            ),
        )
        .order_by("-saldo", "cliente__nome")[:10]
    )
    ranking = []
    for item in ranking_raw:
        vencimento = item["vencimento_mais_antigo"]
        dias_atraso = (hoje - vencimento).days if vencimento else 0
        ranking.append(
            {
                "cliente_id": item["cliente_id"],
                "cliente": item["cliente__nome"],
                "saldo": money(item["saldo"]),
                "dias_em_atraso": max(dias_atraso, 0),
            }
        )

    data = {
        "periodo": {
            "data_inicio": start.isoformat() if start else None,
            "data_fim": end.isoformat() if end else None,
        },
        "kpis": {
            "total_em_aberto": _sum_money(contas_abertas, "valor_restante"),
            "total_vencido": _sum_money(contas_vencidas, "valor_restante"),
            "recebido_no_mes": _sum_money(pagamentos_mes, "valor"),
            "clientes_inadimplentes": contas_vencidas.values("cliente_id").distinct().count(),
        },
        "ranking_maiores_devedores": ranking,
    }
    return data, contas.order_by("-data_abertura", "cliente__nome")


def get_relatorio_vendas(*, company_id: Any, filters: dict[str, Any] | None = None):
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)
    start, end = _period(filters)

    vendas = _vendas_base(company_id).filter(status=Venda.STATUS_CONCLUIDA)
    vendas_periodo = _filter_datetime_period(vendas, "created_at", start, end)

    itens_periodo = _itens_venda_base(company_id).filter(venda__status=Venda.STATUS_CONCLUIDA)
    itens_periodo = _filter_datetime_period(itens_periodo, "venda__created_at", start, end)

    total_periodo = _sum_money(vendas_periodo, "valor_total")
    quantidade_periodo = vendas_periodo.count()
    ticket_medio = money(total_periodo / quantidade_periodo) if quantidade_periodo else ZERO_MONEY

    produtos_mais_vendidos = list(
        itens_periodo.values("produto_id", "produto__nome")
        .annotate(quantidade=Sum("quantidade"), valor_vendido=Sum("subtotal"))
        .order_by("-quantidade", "-valor_vendido", "produto__nome")[:10]
    )
    categorias_mais_vendidas = list(
        itens_periodo.values("produto__categoria_id", "produto__categoria__nome")
        .annotate(quantidade=Sum("quantidade"), valor_vendido=Sum("subtotal"))
        .order_by("-valor_vendido", "-quantidade", "produto__categoria__nome")[:10]
    )
    vendas_por_dia = [
        {
            "data": item["dia"].isoformat(),
            "total": money(item["total"]),
            "quantidade": item["quantidade"],
        }
        for item in (
            vendas_periodo.annotate(dia=TruncDate("created_at"))
            .values("dia")
            .annotate(total=Sum("valor_total"), quantidade=Count("id"))
            .order_by("dia")
        )
    ]

    data = {
        "periodo": {
            "data_inicio": start.isoformat() if start else None,
            "data_fim": end.isoformat() if end else None,
        },
        "kpis": {
            "vendas_hoje": _sum_money(vendas.filter(created_at__date=hoje), "valor_total"),
            "vendas_mes": _sum_money(vendas.filter(created_at__date__gte=inicio_mes), "valor_total"),
            "ticket_medio": ticket_medio,
            "quantidade_vendas": quantidade_periodo,
        },
        "produtos_mais_vendidos": [
            {
                "produto_id": item["produto_id"],
                "produto": item["produto__nome"],
                "quantidade": item["quantidade"] or Decimal("0.000"),
                "valor_vendido": money(item["valor_vendido"]),
            }
            for item in produtos_mais_vendidos
        ],
        "categorias_mais_vendidas": [
            {
                "categoria_id": item["produto__categoria_id"],
                "categoria": item["produto__categoria__nome"],
                "quantidade": item["quantidade"] or Decimal("0.000"),
                "valor_vendido": money(item["valor_vendido"]),
            }
            for item in categorias_mais_vendidas
        ],
        "vendas_por_dia": vendas_por_dia,
    }
    return data, vendas_periodo.order_by("-created_at")


def get_relatorio_financeiro(*, company_id: Any, filters: dict[str, Any] | None = None):
    hoje = timezone.localdate()
    start, end = _period(filters)

    lancamentos = _lancamentos_base(company_id).filter(
        status=LancamentoFinanceiro.STATUS_CONFIRMADO,
    )
    lancamentos_periodo = _filter_datetime_period(lancamentos, "data_lancamento", start, end)
    if tipo := (filters or {}).get("tipo"):
        lancamentos_periodo = lancamentos_periodo.filter(tipo=tipo)

    entradas = _sum_money(
        lancamentos_periodo.filter(tipo=LancamentoFinanceiro.TIPO_ENTRADA),
        "valor",
    )
    saidas = _sum_money(
        lancamentos_periodo.filter(tipo=LancamentoFinanceiro.TIPO_SAIDA),
        "valor",
    )

    fluxo_por_tipo = (
        lancamentos_periodo.annotate(dia=TruncDate("data_lancamento"))
        .values("dia", "tipo")
        .annotate(total=Sum("valor"))
        .order_by("dia", "tipo")
    )
    fluxo_map: dict[date, dict[str, Any]] = {}
    for item in fluxo_por_tipo:
        current = fluxo_map.setdefault(
            item["dia"],
            {"data": item["dia"].isoformat(), "entradas": ZERO_MONEY, "saidas": ZERO_MONEY},
        )
        if item["tipo"] == LancamentoFinanceiro.TIPO_ENTRADA:
            current["entradas"] = money(item["total"])
        else:
            current["saidas"] = money(item["total"])
    fluxo = []
    for item in fluxo_map.values():
        item["saldo"] = money(item["entradas"] - item["saidas"])
        fluxo.append(item)

    contas = _contas_pagar_base(company_id)
    contas_periodo = contas
    if start or end:
        contas_periodo = _filter_date_period(contas_periodo, "data_vencimento", start, end)
    if status := (filters or {}).get("status"):
        contas_periodo = contas_periodo.filter(status=status)

    contas_abertas = contas.filter(
        status=ContaPagar.STATUS_ABERTA,
        valor_restante__gt=ZERO_MONEY,
    )
    contas_a_vencer = contas_abertas.filter(data_vencimento__gte=hoje)
    contas_vencidas = contas_abertas.filter(data_vencimento__lt=hoje)
    contas_pagas = contas.filter(status=ContaPagar.STATUS_PAGA)
    contas_pagas_periodo = _filter_datetime_period(contas_pagas, "data_pagamento", start, end)

    data = {
        "periodo": {
            "data_inicio": start.isoformat() if start else None,
            "data_fim": end.isoformat() if end else None,
        },
        "kpis": {
            "entradas": entradas,
            "saidas": saidas,
            "saldo": money(entradas - saidas),
            "lucro_bruto_estimado": _lucro_bruto_estimado(company_id, start, end),
        },
        "fluxo": fluxo,
        "contas": {
            "a_vencer": {
                "quantidade": contas_a_vencer.count(),
                "total": _sum_money(contas_a_vencer, "valor_restante"),
            },
            "vencidas": {
                "quantidade": contas_vencidas.count(),
                "total": _sum_money(contas_vencidas, "valor_restante"),
            },
            "pagas": {
                "quantidade": contas_pagas_periodo.count(),
                "total": _sum_money(contas_pagas_periodo, "valor_pago"),
            },
        },
    }
    return data, contas_periodo.order_by("data_vencimento", "descricao")


def get_relatorio_estoque(*, company_id: Any, filters: dict[str, Any] | None = None):
    start, end = _period(filters)

    produtos = _produtos_base(company_id).filter(is_active=True)
    if categoria := (filters or {}).get("categoria"):
        produtos = produtos.filter(categoria_id=categoria)
    if search := (filters or {}).get("search"):
        produtos = produtos.filter(
            Q(nome__icontains=search)
            | Q(sku__icontains=search)
            | Q(codigo_barras__icontains=search)
        )

    estoque_expr = ExpressionWrapper(
        F("estoque_atual") * F("custo_medio"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    valor_estoque = money(produtos.aggregate(total=Sum(estoque_expr))["total"])
    produtos_criticos = produtos.filter(estoque_atual__lte=F("estoque_minimo"))

    movimentacoes = _movimentacoes_base(company_id).filter(status=MovimentacaoEstoque.STATUS_ATIVA)
    movimentacoes_periodo = _filter_datetime_period(movimentacoes, "created_at", start, end)
    produtos_movimentados = movimentacoes_periodo.values("produto_id")
    produtos_sem_movimentacao = produtos.exclude(id__in=produtos_movimentados)

    itens_periodo = _itens_venda_base(company_id).filter(venda__status=Venda.STATUS_CONCLUIDA)
    itens_periodo = _filter_datetime_period(itens_periodo, "venda__created_at", start, end)
    if categoria := (filters or {}).get("categoria"):
        itens_periodo = itens_periodo.filter(produto__categoria_id=categoria)

    top_vendidos = [
        {
            "produto_id": item["produto_id"],
            "produto": item["produto__nome"],
            "quantidade": item["quantidade"] or Decimal("0.000"),
            "valor_vendido": money(item["valor_vendido"]),
        }
        for item in (
            itens_periodo.values("produto_id", "produto__nome")
            .annotate(quantidade=Sum("quantidade"), valor_vendido=Sum("subtotal"))
            .order_by("-quantidade", "-valor_vendido", "produto__nome")[:10]
        )
    ]

    ultimas_vendas = (
        _itens_venda_base(company_id)
        .filter(venda__status=Venda.STATUS_CONCLUIDA)
        .values("produto_id")
        .annotate(ultima_venda=Max("venda__created_at"))
    )
    ultima_venda_por_produto = {
        item["produto_id"]: item["ultima_venda"] for item in ultimas_vendas
    }
    top_parados = []
    for produto in produtos_sem_movimentacao.order_by("-estoque_atual", "nome")[:10]:
        ultima = ultima_venda_por_produto.get(produto.pk)
        top_parados.append(
            {
                "produto_id": produto.pk,
                "produto": produto.nome,
                "estoque_atual": produto.estoque_atual,
                "valor_estoque": money(produto.estoque_atual * produto.custo_medio),
                "ultima_venda": ultima.isoformat() if ultima else None,
            }
        )

    data = {
        "periodo": {
            "data_inicio": start.isoformat() if start else None,
            "data_fim": end.isoformat() if end else None,
        },
        "kpis": {
            "valor_estimado_estoque": valor_estoque,
            "produtos_criticos": produtos_criticos.count(),
            "produtos_sem_movimentacao": produtos_sem_movimentacao.count(),
            "produtos_com_maior_giro": itens_periodo.values("produto_id").distinct().count(),
        },
        "top_produtos_vendidos": top_vendidos,
        "top_produtos_parados": top_parados,
    }
    return data, produtos.order_by("nome")
