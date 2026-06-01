import pytest
from django.core.exceptions import ValidationError

from apps.notificacoes.models import (
    CanalNotificacao,
    Notificacao,
    TemplateNotificacao,
    normalizar_telefone,
    validar_telefone_e164,
)


class TestNormalizarTelefone:
    def test_numero_com_55(self):
        assert normalizar_telefone("5583999999999") == "+5583999999999"

    def test_numero_11_digitos(self):
        assert normalizar_telefone("83999999999") == "+5583999999999"

    def test_numero_10_digitos(self):
        assert normalizar_telefone("8332222222") == "+558332222222"

    def test_numero_com_formatacao(self):
        assert normalizar_telefone("+55 (83) 99999-9999") == "+5583999999999"

    def test_ja_normalizado(self):
        assert normalizar_telefone("+5583999999999") == "+5583999999999"


class TestValidarTelefone:
    def test_valido(self):
        validar_telefone_e164("83999999999")

    def test_invalido_vazio(self):
        with pytest.raises(ValidationError):
            validar_telefone_e164("abc")


class TestCanalNotificacao:
    def test_str(self, canal_a):
        assert "WhatsApp" in str(canal_a)

    def test_configuracao_nao_eh_exposto_via_repr(self, canal_a):
        canal_a.configuracao = {"access_token": "super_secret"}
        canal_a.save()
        assert "super_secret" not in str(canal_a)

    def test_unique_canal_ativo_por_tipo_empresa(self, db, empresa_a, admin_user, canal_a):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            CanalNotificacao.objects.create(
                company=empresa_a,
                tipo=CanalNotificacao.TIPO_WHATSAPP,
                nome="Outro Canal",
                provider=CanalNotificacao.PROVIDER_META_CLOUD,
                created_by=admin_user,
            )

    def test_dois_canais_empresas_distintas_ok(self, canal_a, canal_b):
        assert canal_a.company_id != canal_b.company_id


class TestTemplateNotificacao:
    def test_str(self, template_cobranca):
        assert "COBRANCA_FIADO" in str(template_cobranca)

    def test_unique_template_ativo_por_tipo_canal(
        self, db, empresa_a, canal_a, template_cobranca
    ):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TemplateNotificacao.objects.create(
                company=empresa_a,
                canal=canal_a,
                nome="Outro Template",
                tipo=TemplateNotificacao.TIPO_COBRANCA_FIADO,
                provider_template_name="outro_tmpl",
            )


class TestNotificacao:
    def test_ja_enviada_status_enviada(self, db, empresa_a, canal_a):
        n = Notificacao(
            company=empresa_a,
            canal=canal_a,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="Teste",
            destinatario_contato="+5583999999999",
            status=Notificacao.STATUS_ENVIADA,
        )
        assert n.ja_enviada is True

    def test_pode_reenviar_apenas_falhou(self, db, empresa_a, canal_a):
        n = Notificacao(status=Notificacao.STATUS_FALHOU)
        assert n.pode_reenviar is True

        n.status = Notificacao.STATUS_PENDENTE
        assert n.pode_reenviar is False

    def test_idempotency_key_unica_por_empresa(self, db, empresa_a, canal_a):
        from django.db import IntegrityError
        kwargs = dict(
            company=empresa_a,
            canal=canal_a,
            tipo=Notificacao.TIPO_COBRANCA_FIADO,
            destinatario_nome="T",
            destinatario_contato="+5583999999999",
            idempotency_key="chave-unica-123",
        )
        Notificacao.objects.create(**kwargs)
        with pytest.raises(IntegrityError):
            Notificacao.objects.create(**kwargs)
