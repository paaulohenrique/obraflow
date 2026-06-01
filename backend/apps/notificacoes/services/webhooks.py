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

        _aplicar_status_notificacao(msg_id=msg_id, event_type=event_type)

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


def _aplicar_status_notificacao(*, msg_id: str, event_type: str) -> None:
    from apps.notificacoes.models import Notificacao

    if not msg_id:
        return
    novo_status = _STATUS_MAP.get(event_type)
    if not novo_status:
        return

    qs = Notificacao.objects.filter(provider_message_id=msg_id)
    if not qs.exists():
        return

    now = timezone.now()
    update_kwargs: dict[str, Any] = {"status": novo_status, "updated_at": now}

    if novo_status == "ENTREGUE":
        update_kwargs["delivered_at"] = now
    elif novo_status == "LIDA":
        update_kwargs["read_at"] = now
    elif novo_status == "FALHOU":
        update_kwargs["failed_at"] = now

    qs.update(**update_kwargs)
    logger.info(
        "Webhook atualiza Notificacao provider_message_id=%s → %s",
        msg_id,
        novo_status,
    )
