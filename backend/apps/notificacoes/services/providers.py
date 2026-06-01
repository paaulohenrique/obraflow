import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests
from django.conf import settings

logger = logging.getLogger("apps.notificacoes")

_META_BASE = "https://graph.facebook.com"


class WhatsAppError(Exception):
    def __init__(self, code: str, message: str, status_http: int = 0):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_http = status_http


@dataclass(frozen=True)
class SendResult:
    message_id: str
    raw_response: dict[str, Any] = field(default_factory=dict)


class WhatsAppProvider(Protocol):
    name: str

    def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict],
    ) -> SendResult: ...

    def send_text_message(self, *, to: str, body: str) -> SendResult: ...

    def send_document_message(
        self, *, to: str, document_url: str, filename: str, caption: str = ""
    ) -> SendResult: ...


class FakeWhatsAppProvider:
    """Provider para testes — nunca realiza chamadas HTTP."""

    name = "FAKE"

    def __init__(self, *, fail: bool = False):
        self._fail = fail
        self.calls: list[dict] = []

    def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict],
    ) -> SendResult:
        self.calls.append(
            {
                "method": "send_template_message",
                "to": to,
                "template_name": template_name,
                "language_code": language_code,
                "components": components,
            }
        )
        if self._fail:
            raise WhatsAppError("FAKE_FAILURE", "Fake provider configurado para falhar.")
        fake_id = f"fake_wamid_{len(self.calls):04d}"
        return SendResult(message_id=fake_id, raw_response={"fake": True, "wamid": fake_id})

    def send_text_message(self, *, to: str, body: str) -> SendResult:
        self.calls.append({"method": "send_text_message", "to": to, "body": body})
        if self._fail:
            raise WhatsAppError("FAKE_FAILURE", "Fake provider configurado para falhar.")
        fake_id = f"fake_wamid_text_{len(self.calls):04d}"
        return SendResult(message_id=fake_id, raw_response={"fake": True, "wamid": fake_id})

    def send_document_message(
        self, *, to: str, document_url: str, filename: str, caption: str = ""
    ) -> SendResult:
        self.calls.append(
            {
                "method": "send_document_message",
                "to": to,
                "document_url": document_url,
                "filename": filename,
                "caption": caption,
            }
        )
        if self._fail:
            raise WhatsAppError("FAKE_FAILURE", "Fake provider configurado para falhar.")
        fake_id = f"fake_wamid_doc_{len(self.calls):04d}"
        return SendResult(message_id=fake_id, raw_response={"fake": True, "wamid": fake_id})


class MetaCloudWhatsAppProvider:
    """Implementação oficial da Meta WhatsApp Cloud API v{version}."""

    name = "META_CLOUD"

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v23.0",
        timeout: int = 15,
    ):
        if not access_token:
            raise WhatsAppError("CONFIG_ERROR", "access_token não configurado.")
        if not phone_number_id:
            raise WhatsAppError("CONFIG_ERROR", "phone_number_id não configurado.")
        self._token = access_token
        self._phone_number_id = phone_number_id
        self._api_version = api_version
        self._timeout = timeout

    @property
    def _url(self) -> str:
        return f"{_META_BASE}/{self._api_version}/{self._phone_number_id}/messages"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict) -> SendResult:
        try:
            response = requests.post(
                self._url,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            raise WhatsAppError("TIMEOUT", "Timeout ao contatar Meta API.") from exc
        except requests.ConnectionError as exc:
            raise WhatsAppError("CONNECTION_ERROR", "Erro de conexão com Meta API.") from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {}
            error = body.get("error", {})
            code = str(error.get("code", response.status_code))
            msg = error.get("message", response.text[:300])
            logger.error(
                "Meta WhatsApp API error code=%s msg=%s status=%s",
                code,
                msg,
                response.status_code,
            )
            raise WhatsAppError(code, msg, status_http=response.status_code)

        data = response.json()
        messages = data.get("messages", [{}])
        message_id = messages[0].get("id", "") if messages else ""
        return SendResult(message_id=message_id, raw_response=data)

    def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict],
    ) -> SendResult:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }
        return self._post(payload)

    def send_text_message(self, *, to: str, body: str) -> SendResult:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return self._post(payload)

    def send_document_message(
        self, *, to: str, document_url: str, filename: str, caption: str = ""
    ) -> SendResult:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename,
                "caption": caption,
            },
        }
        return self._post(payload)


def get_whatsapp_provider() -> WhatsAppProvider:
    """Resolve provider conforme WHATSAPP_PROVIDER nas settings."""
    provider_name = str(
        getattr(settings, "WHATSAPP_PROVIDER", "FAKE")
    ).upper()

    if provider_name == "META_CLOUD":
        return MetaCloudWhatsAppProvider(
            access_token=getattr(settings, "WHATSAPP_META_ACCESS_TOKEN", ""),
            phone_number_id=getattr(settings, "WHATSAPP_META_PHONE_NUMBER_ID", ""),
            api_version=getattr(settings, "WHATSAPP_META_API_VERSION", "v23.0"),
        )

    return FakeWhatsAppProvider()
