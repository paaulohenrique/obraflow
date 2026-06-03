from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import CharField, OuterRef, Q, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.fiado.models import ContaFiado, PagamentoFiado
from apps.notificacoes.models import Notificacao

from .models import ConfiguracaoCobranca


COBRANCA_TIPOS = (
    Notificacao.TIPO_COBRANCA_FIADO,
    Notificacao.TIPO_LEMBRETE_VENCIMENTO,
    Notificacao.TIPO_COBRANCA_1_DIA,
    Notificacao.TIPO_COBRANCA_7_DIAS,
    Notificacao.TIPO_COBRANCA_15_DIAS,
    Notificacao.TIPO_COBRANCA_30_DIAS,
)


def get_configuracao_cobranca(*, company, user=None) -> ConfiguracaoCobranca:
    configuracao, created = ConfiguracaoCobranca.objects.get_or_create(
        company=company,
        defaults={"updated_by": user},
    )
    if created:
        return configuracao
    return configuracao


def notificacoes_cobranca(company_id, params: dict[str, Any] | None = None) -> QuerySet:
    params = params or {}
    qs = (
        Notificacao.objects.filter(
            company_id=company_id,
            origem_tipo="ContaFiado",
            tipo__in=COBRANCA_TIPOS,
            deleted_at__isnull=True,
        )
        .select_related("canal", "template", "created_by")
        .order_by("-created_at")
    )
    status = params.get("status")
    if status:
        qs = qs.filter(status=status)
    data_inicio = params.get("data_inicio")
    if data_inicio:
        qs = qs.filter(created_at__date__gte=data_inicio)
    data_fim = params.get("data_fim")
    if data_fim:
        qs = qs.filter(created_at__date__lte=data_fim)
    cliente = params.get("cliente")
    if cliente:
        qs = qs.filter(payload__cliente_id=str(cliente))
    return qs


def contas_cobranca(company_id, params: dict[str, Any] | None = None) -> QuerySet:
    params = params or {}
    latest = (
        Notificacao.objects.filter(
            company_id=company_id,
            origem_tipo="ContaFiado",
            origem_id=OuterRef("pk"),
            tipo__in=COBRANCA_TIPOS,
            deleted_at__isnull=True,
        )
        .order_by("-created_at")
    )

    qs = (
        ContaFiado.objects.filter(
            company_id=company_id,
            status=ContaFiado.STATUS_ABERTA,
            valor_restante__gt=0,
            deleted_at__isnull=True,
        )
        .select_related("cliente", "company")
        .annotate(
            status_cobranca=Coalesce(
                Subquery(latest.values("status")[:1]),
                Value(Notificacao.STATUS_PENDENTE),
                output_field=CharField(),
            ),
            ultima_cobranca_id=Subquery(latest.values("id")[:1]),
            ultima_cobranca_tipo=Subquery(latest.values("tipo")[:1]),
            ultima_cobranca_em=Subquery(latest.values("created_at")[:1]),
        )
    )

    cliente = params.get("cliente")
    if cliente:
        qs = qs.filter(cliente_id=cliente)

    search = (params.get("search") or params.get("q") or "").strip()
    if search:
        qs = qs.filter(
            Q(cliente__nome__icontains=search)
            | Q(cliente__cpf_cnpj__icontains=search)
            | Q(cliente__telefone__icontains=search)
            | Q(cliente__whatsapp__icontains=search)
        )

    status = params.get("status")
    if status:
        if status == Notificacao.STATUS_PENDENTE:
            qs = qs.filter(status_cobranca__in=[
                Notificacao.STATUS_PENDENTE,
                Notificacao.STATUS_ENFILEIRADA,
            ])
        else:
            qs = qs.filter(status_cobranca=status)

    data_inicio = params.get("data_inicio")
    if data_inicio:
        qs = qs.filter(data_vencimento__gte=data_inicio)
    data_fim = params.get("data_fim")
    if data_fim:
        qs = qs.filter(data_vencimento__lte=data_fim)

    valor_min = _decimal_param(params.get("valor_min"))
    if valor_min is not None:
        qs = qs.filter(valor_restante__gte=valor_min)
    valor_max = _decimal_param(params.get("valor_max"))
    if valor_max is not None:
        qs = qs.filter(valor_restante__lte=valor_max)

    hoje = timezone.localdate()
    dias_min = _int_param(params.get("dias_atraso_min"))
    if dias_min is not None:
        qs = qs.filter(data_vencimento__lte=hoje - timedelta(days=dias_min))
    dias_max = _int_param(params.get("dias_atraso_max"))
    if dias_max is not None:
        qs = qs.filter(data_vencimento__gte=hoje - timedelta(days=dias_max))

    criterio = _int_param(params.get("criterio"))
    if criterio is not None:
        qs = qs.filter(data_vencimento=hoje - timedelta(days=criterio))

    return qs.order_by("data_vencimento", "cliente__nome")


def dashboard_cobrancas(company_id, params: dict[str, Any] | None = None) -> dict[str, Any]:
    qs = notificacoes_cobranca(company_id, params)

    enviadas = qs.filter(status__in=[
        Notificacao.STATUS_ENVIADA,
        Notificacao.STATUS_ENTREGUE,
        Notificacao.STATUS_LIDA,
    ]).count()
    entregues = qs.filter(status__in=[
        Notificacao.STATUS_ENTREGUE,
        Notificacao.STATUS_LIDA,
    ]).count()
    lidas = qs.filter(status=Notificacao.STATUS_LIDA).count()
    falharam = qs.filter(status=Notificacao.STATUS_FALHOU).count()
    pendentes = qs.filter(status__in=[
        Notificacao.STATUS_PENDENTE,
        Notificacao.STATUS_ENFILEIRADA,
    ]).count()

    valor_cobrado = Decimal("0.00")
    clientes_cobrados: set[str] = set()
    for notificacao in qs:
        payload = notificacao.payload or {}
        valor_cobrado += _decimal_param(payload.get("valor_restante")) or Decimal("0.00")
        cliente_id = payload.get("cliente_id") or notificacao.destinatario_contato
        if cliente_id:
            clientes_cobrados.add(str(cliente_id))

    taxa_entrega = round(entregues / enviadas * 100, 1) if enviadas else 0.0
    taxa_leitura = round(lidas / entregues * 100, 1) if entregues else 0.0

    recuperacao = recuperacao_inadimplencia(company_id, params)

    return {
        "pendentes": pendentes,
        "mensagens_enviadas": enviadas,
        "entregues": entregues,
        "lidas": lidas,
        "falharam": falharam,
        "taxa_entrega": taxa_entrega,
        "taxa_leitura": taxa_leitura,
        "clientes_cobrados": len(clientes_cobrados),
        "valor_cobrado": valor_cobrado,
        "valor_recuperado": recuperacao["valor_recuperado"],
        "percentual_recuperacao": recuperacao["percentual_recuperacao"],
    }


def historico_cobrancas_cliente(company_id, cliente_id) -> QuerySet:
    return notificacoes_cobranca(company_id).filter(payload__cliente_id=str(cliente_id))


def recuperacao_inadimplencia(
    company_id,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qs = notificacoes_cobranca(company_id, params).filter(status__in=[
        Notificacao.STATUS_ENVIADA,
        Notificacao.STATUS_ENTREGUE,
        Notificacao.STATUS_LIDA,
    ]).order_by("created_at")

    primeira_cobranca_por_conta: dict[str, Notificacao] = {}
    for notificacao in qs:
        if not notificacao.origem_id:
            continue
        conta_id = str(notificacao.origem_id)
        if conta_id not in primeira_cobranca_por_conta:
            primeira_cobranca_por_conta[conta_id] = notificacao

    valor_cobrado = Decimal("0.00")
    valor_recuperado = Decimal("0.00")
    for conta_id, notificacao in primeira_cobranca_por_conta.items():
        payload = notificacao.payload or {}
        valor_cobrado += _decimal_param(payload.get("valor_restante")) or Decimal("0.00")
        pagamentos = PagamentoFiado.objects.filter(
            company_id=company_id,
            conta_id=conta_id,
            status=PagamentoFiado.STATUS_CONFIRMADO,
            data_pagamento__gte=notificacao.created_at,
            deleted_at__isnull=True,
        )
        for pagamento in pagamentos:
            valor_recuperado += pagamento.valor

    percentual = (
        round(float(valor_recuperado / valor_cobrado * Decimal("100")), 1)
        if valor_cobrado
        else 0.0
    )

    return {
        "valor_cobrado": valor_cobrado,
        "valor_recuperado": valor_recuperado,
        "percentual_recuperacao": percentual,
    }


def _decimal_param(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _int_param(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
