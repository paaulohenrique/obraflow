from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from .models import CanalNotificacao, Notificacao, TemplateNotificacao


def notificacoes_da_empresa(company_id) -> QuerySet:
    return Notificacao.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
    ).select_related("canal", "template", "created_by")


def templates_da_empresa(company_id) -> QuerySet:
    return TemplateNotificacao.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
    ).select_related("canal")


def canais_da_empresa(company_id) -> QuerySet:
    return CanalNotificacao.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
    )


def dashboard_notificacoes(company_id) -> dict:
    hoje = timezone.localdate()

    qs_hoje = Notificacao.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        created_at__date=hoje,
    )

    pendentes = Notificacao.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        status=Notificacao.STATUS_PENDENTE,
    ).count()

    enviadas_hoje = qs_hoje.filter(status__in=[
        Notificacao.STATUS_ENVIADA,
        Notificacao.STATUS_ENTREGUE,
        Notificacao.STATUS_LIDA,
    ]).count()

    entregues_hoje = qs_hoje.filter(status=Notificacao.STATUS_ENTREGUE).count()
    lidas_hoje = qs_hoje.filter(status=Notificacao.STATUS_LIDA).count()
    falhas_hoje = qs_hoje.filter(status=Notificacao.STATUS_FALHOU).count()

    taxa_entrega = (
        round(entregues_hoje / enviadas_hoje * 100, 1) if enviadas_hoje else 0.0
    )
    taxa_leitura = (
        round(lidas_hoje / entregues_hoje * 100, 1) if entregues_hoje else 0.0
    )

    return {
        "notificacoes_pendentes": pendentes,
        "enviadas_hoje": enviadas_hoje,
        "entregues_hoje": entregues_hoje,
        "lidas_hoje": lidas_hoje,
        "falhas_hoje": falhas_hoje,
        "taxa_entrega": taxa_entrega,
        "taxa_leitura": taxa_leitura,
    }
