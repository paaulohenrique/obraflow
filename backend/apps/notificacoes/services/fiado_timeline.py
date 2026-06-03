"""Registro de timeline fiado a partir das notificações WhatsApp."""
from __future__ import annotations

from typing import Any


def registrar_evento_cobranca_fiado(*, notificacao, status: str, extra: dict[str, Any] | None = None) -> None:
    """Cria evento de histórico do fiado quando uma cobrança muda de status."""
    if notificacao.origem_tipo != "ContaFiado" or not notificacao.origem_id:
        return

    from apps.fiado.models import ContaFiado, HistoricoFiado
    from apps.fiado.services.conta import criar_historico_fiado
    from apps.notificacoes.models import Notificacao

    evento_por_status = {
        Notificacao.STATUS_ENVIADA: HistoricoFiado.EVENTO_COBRANCA_ENVIADA,
        Notificacao.STATUS_ENTREGUE: HistoricoFiado.EVENTO_COBRANCA_ENTREGUE,
        Notificacao.STATUS_LIDA: HistoricoFiado.EVENTO_COBRANCA_LIDA,
        Notificacao.STATUS_FALHOU: HistoricoFiado.EVENTO_COBRANCA_FALHOU,
    }
    evento = evento_por_status.get(status)
    if not evento:
        return

    if HistoricoFiado.objects.filter(
        company_id=notificacao.company_id,
        conta_id=notificacao.origem_id,
        evento=evento,
        metadata__notificacao_id=str(notificacao.pk),
        deleted_at__isnull=True,
    ).exists():
        return

    conta = (
        ContaFiado.objects.filter(
            pk=notificacao.origem_id,
            company_id=notificacao.company_id,
            deleted_at__isnull=True,
        )
        .select_related("cliente", "company")
        .first()
    )
    if not conta:
        return

    descricao_por_status = {
        Notificacao.STATUS_ENVIADA: "Cobrança WhatsApp enviada.",
        Notificacao.STATUS_ENTREGUE: "Mensagem de cobrança entregue ao cliente.",
        Notificacao.STATUS_LIDA: "Mensagem de cobrança lida pelo cliente.",
        Notificacao.STATUS_FALHOU: "Falha no envio da cobrança WhatsApp.",
    }
    metadata = {
        "notificacao_id": str(notificacao.pk),
        "notificacao_status": status,
        "provider_message_id": notificacao.provider_message_id,
        "tipo_notificacao": notificacao.tipo,
    }
    if extra:
        metadata.update(extra)

    criar_historico_fiado(
        user=notificacao.created_by,
        conta=conta,
        evento=evento,
        descricao=descricao_por_status[status],
        metadata=metadata,
    )
