from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.core.models import AuditLog
from apps.fiado.models import HistoricoFiado
from apps.notificacoes.models import Notificacao, TemplateNotificacao
from apps.notificacoes.services.providers import FakeWhatsAppProvider
from apps.notificacoes.services.webhooks import processar_evento_webhook
from apps.notificacoes.services.whatsapp import NotificacaoError, executar_envio

from apps.cobrancas.selectors import dashboard_cobrancas
from apps.cobrancas.services import (
    enviar_cobranca_conta,
    enviar_cobranca_lote,
    garantir_templates_operacionais,
    montar_preview_cobranca,
)

from .conftest import make_cliente, make_conta


@pytest.mark.django_db
class TestCobrancaIndividual:
    def test_preview_usa_template_operacional(self, admin_user, empresa_a, canal_a):
        cliente = make_cliente(empresa_a, nome="João")
        conta = make_conta(
            empresa_a,
            cliente,
            vencimento=timezone.localdate() - timedelta(days=1),
        )
        garantir_templates_operacionais(company=empresa_a, user=admin_user)

        preview = montar_preview_cobranca(conta=conta)

        assert preview["tipo"] == Notificacao.TIPO_COBRANCA_1_DIA
        assert preview["cliente_nome"] == "João"
        assert "R$ 250.00" in preview["mensagem"]
        assert "MP Construções" in preview["mensagem"]

    def test_enviar_cria_notificacao_template_payload_e_auditlog(self, admin_user, empresa_a, canal_a):
        cliente = make_cliente(empresa_a, nome="Maria")
        conta = make_conta(
            empresa_a,
            cliente,
            vencimento=timezone.localdate() - timedelta(days=7),
            valor=Decimal("320.00"),
        )

        with patch("apps.notificacoes.tasks.enviar_notificacao_whatsapp.apply_async") as apply_async:
            notificacao = enviar_cobranca_conta(conta=conta, user=admin_user)

        assert notificacao.tipo == Notificacao.TIPO_COBRANCA_7_DIAS
        assert notificacao.status == Notificacao.STATUS_PENDENTE
        assert notificacao.origem_tipo == "ContaFiado"
        assert notificacao.origem_id == conta.pk
        assert notificacao.destinatario_contato == "+5585999990000"
        assert notificacao.payload["cliente_id"] == str(cliente.pk)
        assert notificacao.payload["valor_restante"] == "320.00"
        assert TemplateNotificacao.objects.filter(
            company=empresa_a,
            tipo=Notificacao.TIPO_COBRANCA_7_DIAS,
            ativo=True,
        ).exists()
        assert AuditLog.objects.filter(entity_type="Notificacao", entity_id=notificacao.pk).exists()
        apply_async.assert_called_once()

    def test_cliente_sem_telefone_falha(self, admin_user, empresa_a, canal_a):
        cliente = make_cliente(empresa_a, telefone="", whatsapp="")
        conta = make_conta(
            empresa_a,
            cliente,
            vencimento=timezone.localdate() - timedelta(days=1),
        )

        with pytest.raises(NotificacaoError) as exc_info:
            enviar_cobranca_conta(conta=conta, user=admin_user)

        assert exc_info.value.code == "SEM_TELEFONE"

    def test_nao_permite_cobrar_conta_de_outra_empresa(
        self,
        admin_user,
        empresa_b,
        canal_a,
        canal_b,
    ):
        cliente = make_cliente(empresa_b)
        conta = make_conta(
            empresa_b,
            cliente,
            vencimento=timezone.localdate() - timedelta(days=1),
        )

        with pytest.raises(NotificacaoError) as exc_info:
            enviar_cobranca_conta(conta=conta, user=admin_user)

        assert exc_info.value.code == "CONTA_NAO_ENCONTRADA"


@pytest.mark.django_db
class TestCobrancaLote:
    def test_lote_envia_apenas_criterio_selecionado(self, admin_user, empresa_a, canal_a):
        cliente_1 = make_cliente(empresa_a, nome="Cliente 1")
        cliente_7 = make_cliente(empresa_a, nome="Cliente 7")
        make_conta(
            empresa_a,
            cliente_1,
            vencimento=timezone.localdate() - timedelta(days=1),
            valor=Decimal("100.00"),
        )
        make_conta(
            empresa_a,
            cliente_7,
            vencimento=timezone.localdate() - timedelta(days=7),
            valor=Decimal("700.00"),
        )

        with patch("apps.notificacoes.tasks.enviar_notificacao_whatsapp.apply_async"):
            resultado = enviar_cobranca_lote(user=admin_user, criterio=1)

        assert resultado.quantidade == 1
        assert resultado.valor_total == Decimal("100.00")
        assert resultado.notificacoes[0].tipo == Notificacao.TIPO_COBRANCA_1_DIA
        assert resultado.falhas == []


@pytest.mark.django_db
class TestDashboardCobrancas:
    def test_dashboard_calcula_kpis(self, empresa_a, canal_a):
        statuses = [
            (Notificacao.STATUS_ENVIADA, "100.00", "1"),
            (Notificacao.STATUS_ENTREGUE, "200.00", "2"),
            (Notificacao.STATUS_LIDA, "300.00", "3"),
            (Notificacao.STATUS_FALHOU, "400.00", "4"),
        ]
        for status, valor, cliente_id in statuses:
            Notificacao.objects.create(
                company=empresa_a,
                canal=canal_a,
                tipo=Notificacao.TIPO_COBRANCA_1_DIA,
                destinatario_nome=f"Cliente {cliente_id}",
                destinatario_contato="+558599990000",
                mensagem="Cobrança",
                payload={"valor_restante": valor, "cliente_id": cliente_id},
                status=status,
                origem_tipo="ContaFiado",
            )

        data = dashboard_cobrancas(empresa_a.pk)

        assert data["mensagens_enviadas"] == 3
        assert data["entregues"] == 2
        assert data["lidas"] == 1
        assert data["falharam"] == 1
        assert data["taxa_entrega"] == 66.7
        assert data["taxa_leitura"] == 50.0
        assert data["clientes_cobrados"] == 4
        assert data["valor_cobrado"] == Decimal("1000.00")


@pytest.mark.django_db
class TestTimelineCobranca:
    def test_envio_e_webhook_registram_timeline(self, admin_user, empresa_a, canal_a):
        cliente = make_cliente(empresa_a)
        conta = make_conta(
            empresa_a,
            cliente,
            vencimento=timezone.localdate() - timedelta(days=1),
        )
        notificacao = Notificacao.objects.create(
            company=empresa_a,
            canal=canal_a,
            tipo=Notificacao.TIPO_COBRANCA_1_DIA,
            destinatario_nome=cliente.nome,
            destinatario_contato="85999990000",
            mensagem="Cobrança",
            payload={"cliente_id": str(cliente.pk), "valor_restante": "250.00"},
            origem_tipo="ContaFiado",
            origem_id=conta.pk,
            created_by=admin_user,
        )

        executar_envio(notificacao=notificacao, provider=FakeWhatsAppProvider())
        notificacao.refresh_from_db()
        processar_evento_webhook(_payload_status(notificacao.provider_message_id, "delivered"))
        processar_evento_webhook(_payload_status(notificacao.provider_message_id, "read"))
        processar_evento_webhook(_payload_status(notificacao.provider_message_id, "read"))

        eventos = list(
            HistoricoFiado.objects.filter(conta=conta).values_list("evento", flat=True)
        )
        assert HistoricoFiado.EVENTO_COBRANCA_ENVIADA in eventos
        assert HistoricoFiado.EVENTO_COBRANCA_ENTREGUE in eventos
        assert eventos.count(HistoricoFiado.EVENTO_COBRANCA_LIDA) == 1


def _payload_status(message_id: str, status: str):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": message_id,
                                    "status": status,
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
