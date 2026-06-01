import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.notificacoes.models import Notificacao
from apps.notificacoes.services.providers import (
    FakeWhatsAppProvider,
    MetaCloudWhatsAppProvider,
    SendResult,
    WhatsAppError,
)
from apps.notificacoes.services.whatsapp import (
    NotificacaoError,
    criar_notificacao,
    enviar_cobranca_fiado,
    enviar_confirmacao_pagamento,
    enviar_lembrete_vencimento,
    executar_envio,
)


# ──────────────────────────────────────────────
# Providers
# ──────────────────────────────────────────────

class TestFakeWhatsAppProvider:
    def test_send_template_retorna_result(self):
        p = FakeWhatsAppProvider()
        result = p.send_template_message(
            to="+5583999999999",
            template_name="tmpl",
            language_code="pt_BR",
            components=[],
        )
        assert isinstance(result, SendResult)
        assert result.message_id.startswith("fake_wamid")
        assert len(p.calls) == 1

    def test_send_text_retorna_result(self):
        p = FakeWhatsAppProvider()
        result = p.send_text_message(to="+5583999999999", body="Olá")
        assert result.message_id

    def test_send_document_retorna_result(self):
        p = FakeWhatsAppProvider()
        result = p.send_document_message(
            to="+5583999999999",
            document_url="https://example.com/doc.pdf",
            filename="doc.pdf",
        )
        assert result.message_id

    def test_fail_mode(self):
        p = FakeWhatsAppProvider(fail=True)
        with pytest.raises(WhatsAppError) as exc_info:
            p.send_text_message(to="+5583999999999", body="Teste")
        assert exc_info.value.code == "FAKE_FAILURE"

    def test_calls_registram_todos_metodos(self):
        p = FakeWhatsAppProvider()
        p.send_template_message(to="+55", template_name="t", language_code="pt_BR", components=[])
        p.send_text_message(to="+55", body="b")
        p.send_document_message(to="+55", document_url="u", filename="f")
        assert len(p.calls) == 3


class TestMetaCloudProviderConfig:
    def test_sem_token_levanta_erro(self):
        with pytest.raises(WhatsAppError) as exc_info:
            MetaCloudWhatsAppProvider(access_token="", phone_number_id="123")
        assert exc_info.value.code == "CONFIG_ERROR"

    def test_sem_phone_id_levanta_erro(self):
        with pytest.raises(WhatsAppError):
            MetaCloudWhatsAppProvider(access_token="token", phone_number_id="")


# ──────────────────────────────────────────────
# criar_notificacao
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestCriarNotificacao:
    def test_cria_pendente(self, empresa_a, canal_a):
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
        )
        assert n.status == Notificacao.STATUS_PENDENTE
        assert n.destinatario_contato == "+5583999999999"

    def test_idempotencia_retorna_existente(self, empresa_a, canal_a):
        kwargs = dict(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
            idempotency_key="chave-idem-001",
        )
        n1 = criar_notificacao(**kwargs)
        n2 = criar_notificacao(**kwargs)
        assert n1.pk == n2.pk

    def test_sem_canal_ativo_levanta_erro(self, db, empresa_b, canal_b):
        canal_b.ativo = False
        canal_b.save()
        with pytest.raises(NotificacaoError) as exc_info:
            criar_notificacao(
                company_id=empresa_b.pk,
                tipo=Notificacao.TIPO_COBRANCA_FIADO,
                destinatario_nome="X",
                destinatario_contato="83999999999",
            )
        assert exc_info.value.code == "CANAL_INDISPONIVEL"

    def test_normaliza_telefone(self, empresa_a, canal_a):
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="X",
            destinatario_contato="(83) 9 9999-9999",
        )
        assert n.destinatario_contato == "+5583999999999"


# ──────────────────────────────────────────────
# executar_envio
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestExecutarEnvio:
    def test_envio_fake_sucesso(self, empresa_a, canal_a):
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
            mensagem="Teste",
        )
        provider = FakeWhatsAppProvider()
        resultado = executar_envio(notificacao=n, provider=provider)
        assert resultado.status == Notificacao.STATUS_ENVIADA
        assert resultado.provider_message_id.startswith("fake_wamid")
        assert resultado.sent_at is not None

    def test_envio_fake_falha(self, empresa_a, canal_a):
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
            mensagem="Teste",
        )
        provider = FakeWhatsAppProvider(fail=True)
        with pytest.raises(WhatsAppError):
            executar_envio(notificacao=n, provider=provider)
        n.refresh_from_db()
        assert n.status == Notificacao.STATUS_FALHOU
        assert n.erro_codigo == "FAKE_FAILURE"
        assert n.failed_at is not None

    def test_ja_enviada_nao_reenvia(self, empresa_a, canal_a):
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
        )
        provider = FakeWhatsAppProvider()
        executar_envio(notificacao=n, provider=provider)
        n.refresh_from_db()
        primeiro_id = n.provider_message_id

        # segunda chamada deve ser ignorada
        executar_envio(notificacao=n, provider=provider)
        n.refresh_from_db()
        assert n.provider_message_id == primeiro_id
        assert len(provider.calls) == 1

    def test_usa_template_quando_configurado(self, empresa_a, canal_a, template_cobranca):
        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="João",
            destinatario_contato="83999999999",
            payload={"componentes": [{"type": "body", "parameters": []}]},
        )
        n.template = template_cobranca
        n.save()

        provider = FakeWhatsAppProvider()
        executar_envio(notificacao=n, provider=provider)
        assert provider.calls[0]["method"] == "send_template_message"
        assert provider.calls[0]["template_name"] == "cobranca_fiado_v1"


# ──────────────────────────────────────────────
# enviar_cobranca_fiado
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEnviarCobrancaFiado:
    def test_cria_notificacao(
        self, empresa_a, canal_a, template_cobranca, conta_fiado_a, admin_user
    ):
        n = enviar_cobranca_fiado(conta_fiado_id=conta_fiado_a.pk, created_by=admin_user)
        assert n.tipo == Notificacao.TIPO_COBRANCA_FIADO
        assert n.origem_tipo == "ContaFiado"
        assert str(n.origem_id) == str(conta_fiado_a.pk)
        assert n.status == Notificacao.STATUS_PENDENTE

    def test_idempotente_mesmo_conta(
        self, empresa_a, canal_a, template_cobranca, conta_fiado_a, admin_user
    ):
        n1 = enviar_cobranca_fiado(conta_fiado_id=conta_fiado_a.pk, created_by=admin_user)
        n2 = enviar_cobranca_fiado(conta_fiado_id=conta_fiado_a.pk, created_by=admin_user)
        assert n1.pk == n2.pk

    def test_sem_telefone_levanta_erro(self, empresa_a, canal_a, admin_user):
        from apps.clientes.models import Cliente
        cliente_sem_tel = Cliente.objects.create(
            company=empresa_a,
            nome="Sem Tel",
            cpf_cnpj="98765432100",
            tipo_pessoa=Cliente.TIPO_PF,
            telefone="",
        )
        from apps.fiado.services.conta import abrir_conta_fiado
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente_sem_tel})
        with pytest.raises(NotificacaoError) as exc_info:
            enviar_cobranca_fiado(conta_fiado_id=conta.pk, created_by=admin_user)
        assert exc_info.value.code == "SEM_TELEFONE"


# ──────────────────────────────────────────────
# enviar_confirmacao_pagamento
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEnviarConfirmacaoPagamento:
    def test_cria_notificacao(
        self, empresa_a, canal_a, template_confirmacao, pagamento_fiado_a, admin_user
    ):
        n = enviar_confirmacao_pagamento(
            pagamento_fiado_id=pagamento_fiado_a.pk, created_by=admin_user
        )
        assert n.tipo == Notificacao.TIPO_CONFIRMACAO_PAGAMENTO
        assert n.origem_tipo == "PagamentoFiado"

    def test_idempotente(
        self, empresa_a, canal_a, template_confirmacao, pagamento_fiado_a, admin_user
    ):
        n1 = enviar_confirmacao_pagamento(
            pagamento_fiado_id=pagamento_fiado_a.pk, created_by=admin_user
        )
        n2 = enviar_confirmacao_pagamento(
            pagamento_fiado_id=pagamento_fiado_a.pk, created_by=admin_user
        )
        assert n1.pk == n2.pk


# ──────────────────────────────────────────────
# enviar_lembrete_vencimento
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEnviarLembreteVencimento:
    def test_cria_notificacao(
        self, empresa_a, canal_a, admin_user, conta_fiado_a
    ):
        from django.utils import timezone
        conta_fiado_a.data_vencimento = timezone.localdate()
        conta_fiado_a.save()

        n = enviar_lembrete_vencimento(
            conta_fiado_id=conta_fiado_a.pk, created_by=admin_user
        )
        assert n.tipo == Notificacao.TIPO_LEMBRETE_VENCIMENTO

    def test_sem_vencimento_levanta_erro(self, empresa_a, canal_a, admin_user, conta_fiado_a):
        conta_fiado_a.data_vencimento = None
        conta_fiado_a.save()
        with pytest.raises(NotificacaoError) as exc_info:
            enviar_lembrete_vencimento(conta_fiado_id=conta_fiado_a.pk, created_by=admin_user)
        assert exc_info.value.code == "SEM_VENCIMENTO"


# ──────────────────────────────────────────────
# Rate limit
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestRateLimit:
    def test_rate_limit_bloqueia_apos_limite(self, empresa_a, canal_a, settings):
        from django.core.cache import cache
        from apps.notificacoes.services.whatsapp import _RATE_LIMIT_PER_MINUTE, _verificar_rate_limit

        cache.clear()
        key = f"notif_wpp_rate:{empresa_a.pk}"
        cache.set(key, _RATE_LIMIT_PER_MINUTE, 60)

        with pytest.raises(NotificacaoError) as exc_info:
            _verificar_rate_limit(empresa_a.pk)
        assert exc_info.value.code == "RATE_LIMIT"
        cache.clear()


# ──────────────────────────────────────────────
# Task Celery
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestCeleryTask:
    def test_task_envia_notificacao(self, empresa_a, canal_a, settings):
        settings.WHATSAPP_PROVIDER = "FAKE"
        from apps.notificacoes.tasks import enviar_notificacao_whatsapp

        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="Task User",
            destinatario_contato="83999999999",
            mensagem="Teste task",
        )
        enviar_notificacao_whatsapp.apply(args=[str(n.pk)])
        n.refresh_from_db()
        assert n.status == Notificacao.STATUS_ENVIADA

    def test_task_notificacao_inexistente_nao_lanca(self, db, settings):
        settings.WHATSAPP_PROVIDER = "FAKE"
        from apps.notificacoes.tasks import enviar_notificacao_whatsapp
        # Deve retornar silenciosamente
        enviar_notificacao_whatsapp.apply(args=[str(uuid.uuid4())])

    def test_task_ja_enviada_ignora(self, empresa_a, canal_a, settings):
        settings.WHATSAPP_PROVIDER = "FAKE"
        from apps.notificacoes.tasks import enviar_notificacao_whatsapp

        n = criar_notificacao(
            company_id=empresa_a.pk,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="X",
            destinatario_contato="83999999999",
        )
        n.status = Notificacao.STATUS_ENVIADA
        n.save()

        provider = FakeWhatsAppProvider()
        with patch(
            "apps.notificacoes.services.providers.get_whatsapp_provider", return_value=provider
        ):
            enviar_notificacao_whatsapp.apply(args=[str(n.pk)])
        assert len(provider.calls) == 0
