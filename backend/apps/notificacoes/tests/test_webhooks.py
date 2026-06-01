import pytest

from apps.notificacoes.models import EventoWebhookWhatsApp, Notificacao
from apps.notificacoes.services.webhooks import processar_evento_webhook
from apps.notificacoes.services.whatsapp import criar_notificacao


def _payload_status(msg_id: str, status: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": msg_id,
                                    "status": status,
                                    "timestamp": "1716000000",
                                    "recipient_id": "5583999999999",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


# ──────────────────────────────────────────────
# Webhook GET verify
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhookGet:
    def test_verify_token_correto(self, anon_client, settings):
        settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN = "meu-token-secreto"
        url = "/api/v1/notificacoes/whatsapp/webhook/"
        resp = anon_client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "meu-token-secreto",
                "hub.challenge": "42",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == 42

    def test_verify_token_errado(self, anon_client, settings):
        settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN = "correto"
        url = "/api/v1/notificacoes/whatsapp/webhook/"
        resp = anon_client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "errado",
                "hub.challenge": "42",
            },
        )
        assert resp.status_code == 403


# ──────────────────────────────────────────────
# Webhook POST — processar_evento_webhook
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestProcessarEventoWebhook:
    def _criar_notificacao_enviada(self, empresa_a, canal_a, msg_id: str) -> Notificacao:
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
        )
        n.status = Notificacao.STATUS_ENVIADA
        n.provider_message_id = msg_id
        n.save()
        return n

    def test_webhook_delivered_atualiza_status(self, db, empresa_a, canal_a):
        msg_id = "wamid_delivered_001"
        n = self._criar_notificacao_enviada(empresa_a, canal_a, msg_id)

        processar_evento_webhook(_payload_status(msg_id, "delivered"))

        n.refresh_from_db()
        assert n.status == Notificacao.STATUS_ENTREGUE
        assert n.delivered_at is not None

    def test_webhook_read_atualiza_status(self, db, empresa_a, canal_a):
        msg_id = "wamid_read_001"
        n = self._criar_notificacao_enviada(empresa_a, canal_a, msg_id)

        processar_evento_webhook(_payload_status(msg_id, "read"))

        n.refresh_from_db()
        assert n.status == Notificacao.STATUS_LIDA
        assert n.read_at is not None

    def test_webhook_failed_atualiza_status(self, db, empresa_a, canal_a):
        msg_id = "wamid_fail_001"
        n = self._criar_notificacao_enviada(empresa_a, canal_a, msg_id)

        processar_evento_webhook(_payload_status(msg_id, "failed"))

        n.refresh_from_db()
        assert n.status == Notificacao.STATUS_FALHOU
        assert n.failed_at is not None

    def test_webhook_salva_evento(self, db, empresa_a, canal_a):
        msg_id = "wamid_evt_save_001"
        self._criar_notificacao_enviada(empresa_a, canal_a, msg_id)
        processar_evento_webhook(_payload_status(msg_id, "delivered"))

        evento = EventoWebhookWhatsApp.objects.get(provider_message_id=msg_id)
        assert evento.processed is True
        assert evento.event_type == "delivered"

    def test_webhook_idempotente(self, db, empresa_a, canal_a):
        msg_id = "wamid_idem_001"
        n = self._criar_notificacao_enviada(empresa_a, canal_a, msg_id)
        payload = _payload_status(msg_id, "delivered")

        processar_evento_webhook(payload)
        processar_evento_webhook(payload)

        count = EventoWebhookWhatsApp.objects.filter(provider_message_id=msg_id).count()
        assert count == 1

    def test_webhook_payload_vazio_nao_explode(self, db):
        processar_evento_webhook({})
        assert EventoWebhookWhatsApp.objects.filter(event_type="unknown").exists()

    def test_webhook_msg_id_desconhecido_nao_explode(self, db):
        processar_evento_webhook(_payload_status("wamid_unknown_xyz", "delivered"))


# ──────────────────────────────────────────────
# Webhook POST via API
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhookPostAPI:
    def test_post_retorna_200_sempre(self, anon_client):
        url = "/api/v1/notificacoes/whatsapp/webhook/"
        resp = anon_client.post(url, data={}, format="json")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_post_payload_invalido_nao_retorna_500(self, anon_client):
        url = "/api/v1/notificacoes/whatsapp/webhook/"
        resp = anon_client.post(
            url,
            data={"garbage": "data", "nested": {"deep": [1, 2, 3]}},
            format="json",
        )
        assert resp.status_code == 200
