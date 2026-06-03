"""Processamento de eventos Webhook da Meta WhatsApp Cloud API."""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.notificacoes")

_STATUS_MAP = {
    "delivered": "ENTREGUE",
    "read": "LIDA",
    "failed": "FALHOU",
    "sent": "ENVIADA",
}

_STATUS_RANK = {
    "PENDENTE": 0,
    "ENFILEIRADA": 1,
    "ENVIADA": 2,
    "ENTREGUE": 3,
    "LIDA": 4,
    "FALHOU": 5,
    "CANCELADA": 5,
}


def verificar_assinatura_webhook(
    payload_bytes: bytes, signature_header: str
) -> bool:
    """Valida X-Hub-Signature-256 opcional da Meta."""
    secret = getattr(settings, "WHATSAPP_META_APP_SECRET", "")
    if not secret:
        return True
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


def _extrair_statuses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna lista de status updates do payload Meta."""
    statuses = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for s in value.get("statuses", []):
                statuses.append(s)
    return statuses


def processar_evento_webhook(
    payload: dict[str, Any],
    *,
    company=None,
) -> None:
    """Salva EventoWebhookWhatsApp e atualiza status das Notificacoes."""
    from apps.notificacoes.models import EventoWebhookWhatsApp, Notificacao

    statuses = _extrair_statuses(payload)

    for status_entry in statuses:
        msg_id = status_entry.get("id", "")
        event_type = status_entry.get("status", "")

        evento = EventoWebhookWhatsApp.objects.filter(
            provider_message_id=msg_id,
            event_type=event_type,
        ).first()
        if evento and evento.processed:
            continue

        if not evento:
            evento = EventoWebhookWhatsApp.objects.create(
                company=company,
                provider="META_CLOUD",
                event_type=event_type,
                provider_message_id=msg_id,
                payload=status_entry,
            )

        _aplicar_status_notificacao(
            msg_id=msg_id,
            event_type=event_type,
            payload=status_entry,
        )

        evento.processed = True
        evento.save(update_fields=["processed"])

    if not statuses:
        EventoWebhookWhatsApp.objects.create(
            company=company,
            provider="META_CLOUD",
            event_type="unknown",
            provider_message_id="",
            payload=payload,
            processed=True,
        )


def _aplicar_status_notificacao(
    *,
    msg_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    from apps.notificacoes.models import Notificacao
    from apps.notificacoes.services.fiado_timeline import registrar_evento_cobranca_fiado

    if not msg_id:
        return
    novo_status = _STATUS_MAP.get(event_type)
    if not novo_status:
        return

    qs = Notificacao.objects.filter(provider_message_id=msg_id)
    if not qs.exists():
        return

    now = timezone.now()
    erro_codigo = ""
    erro_mensagem = ""
    errors = (payload or {}).get("errors") or []
    if errors:
        first_error = errors[0]
        erro_codigo = str(first_error.get("code", ""))
        erro_mensagem = first_error.get("message") or first_error.get("title") or ""

    for notificacao in qs:
        if _STATUS_RANK.get(novo_status, 0) < _STATUS_RANK.get(notificacao.status, 0):
            continue

        notificacao.status = novo_status
        update_fields = ["status", "updated_at"]

        if novo_status == "ENTREGUE":
            notificacao.delivered_at = notificacao.delivered_at or now
            update_fields.append("delivered_at")
        elif novo_status == "LIDA":
            notificacao.read_at = notificacao.read_at or now
            update_fields.append("read_at")
        elif novo_status == "FALHOU":
            notificacao.failed_at = notificacao.failed_at or now
            update_fields.append("failed_at")
            if erro_codigo:
                notificacao.erro_codigo = erro_codigo
                update_fields.append("erro_codigo")
            if erro_mensagem:
                notificacao.erro_mensagem = erro_mensagem
                update_fields.append("erro_mensagem")

        notificacao.save(update_fields=update_fields)
        registrar_evento_cobranca_fiado(
            notificacao=notificacao,
            status=novo_status,
            extra={"webhook_event_type": event_type},
        )
        logger.info(
            "Webhook atualiza Notificacao provider_message_id=%s → %s",
            msg_id,
            novo_status,
        )
