import pytest

from apps.notificacoes.models import CanalNotificacao, Notificacao, TemplateNotificacao
from apps.notificacoes.services.whatsapp import criar_notificacao

BASE = "/api/v1/notificacoes"


def _criar_notif(empresa, canal, tipo=Notificacao.TIPO_COBRANCA_FIADO):
    return criar_notificacao(
        company_id=empresa.pk,
        tipo=tipo,
        destinatario_nome="João",
        destinatario_contato="83999999999",
    )


# ──────────────────────────────────────────────
# Permissões — autenticação
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestNotificacaoPermissoes:
    def test_anonimo_retorna_401(self, anon_client):
        resp = anon_client.get(f"{BASE}/notificacoes/")
        assert resp.status_code == 401

    def test_viewer_pode_listar(self, viewer_client, empresa_a, canal_a):
        _criar_notif(empresa_a, canal_a)
        resp = viewer_client.get(f"{BASE}/notificacoes/")
        assert resp.status_code == 200

    def test_seller_pode_listar(self, seller_client, empresa_a, canal_a):
        resp = seller_client.get(f"{BASE}/notificacoes/")
        assert resp.status_code == 200

    def test_manager_pode_listar(self, manager_client, empresa_a, canal_a):
        resp = manager_client.get(f"{BASE}/notificacoes/")
        assert resp.status_code == 200


# ──────────────────────────────────────────────
# Isolamento multi-tenant
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestMultiTenant:
    def test_empresa_a_nao_ve_notificacoes_empresa_b(
        self, admin_client, empresa_a, canal_a, empresa_b, canal_b
    ):
        _criar_notif(empresa_a, canal_a)
        _criar_notif(empresa_b, canal_b)

        resp = admin_client.get(f"{BASE}/notificacoes/")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["results"]]
        # todos os ids devem pertencer à empresa_a
        notifs_b = Notificacao.objects.filter(company=empresa_b)
        for nid in ids:
            assert not notifs_b.filter(pk=nid).exists()

    def test_canal_empresa_b_nao_aparece_em_empresa_a(
        self, admin_client, canal_b
    ):
        resp = admin_client.get(f"{BASE}/canais/")
        canal_ids = [r["id"] for r in resp.json()["results"]]
        assert str(canal_b.pk) not in canal_ids


# ──────────────────────────────────────────────
# Canais
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestCanalAPI:
    def test_listar_canais(self, admin_client, canal_a):
        resp = admin_client.get(f"{BASE}/canais/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_criar_canal(self, admin_client, empresa_a):
        resp = admin_client.post(
            f"{BASE}/canais/",
            {"tipo": "EMAIL", "nome": "E-mail Geral", "ativo": True, "provider": "META_CLOUD"},
            format="json",
        )
        assert resp.status_code == 201

    def test_token_nao_aparece_na_resposta(self, admin_client, canal_a):
        canal_a.configuracao = {"access_token": "meu_token_secreto"}
        canal_a.save()
        resp = admin_client.get(f"{BASE}/canais/{canal_a.pk}/")
        assert resp.status_code == 200
        assert "access_token" not in str(resp.json())
        assert "meu_token_secreto" not in str(resp.json())

    def test_viewer_nao_pode_criar_canal(self, viewer_client):
        resp = viewer_client.post(
            f"{BASE}/canais/",
            {"tipo": "EMAIL", "nome": "X", "ativo": True, "provider": "META_CLOUD"},
            format="json",
        )
        assert resp.status_code == 403


# ──────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestTemplateAPI:
    def test_listar_templates(self, admin_client, template_cobranca):
        resp = admin_client.get(f"{BASE}/templates/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_criar_template(self, admin_client, canal_a):
        resp = admin_client.post(
            f"{BASE}/templates/",
            {
                "canal": str(canal_a.pk),
                "nome": "Novo Template",
                "tipo": "RESUMO_CONTA",
                "provider_template_name": "resumo_v1",
                "linguagem": "pt_BR",
                "categoria": "UTILITY",
                "corpo": "Olá {nome}",
                "variaveis": ["nome"],
                "ativo": True,
            },
            format="json",
        )
        assert resp.status_code == 201

    def test_canal_de_outra_empresa_rejeitado(
        self, admin_client, canal_b
    ):
        resp = admin_client.post(
            f"{BASE}/templates/",
            {
                "canal": str(canal_b.pk),
                "nome": "Hack",
                "tipo": "RESUMO_CONTA",
                "provider_template_name": "x",
                "linguagem": "pt_BR",
                "categoria": "UTILITY",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_viewer_nao_pode_criar_template(self, viewer_client, canal_a):
        resp = viewer_client.post(
            f"{BASE}/templates/",
            {
                "canal": str(canal_a.pk),
                "nome": "X",
                "tipo": "RESUMO_CONTA",
                "provider_template_name": "x",
                "linguagem": "pt_BR",
                "categoria": "UTILITY",
            },
            format="json",
        )
        assert resp.status_code == 403


# ──────────────────────────────────────────────
# Notificações
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestNotificacaoAPI:
    def test_listar(self, admin_client, empresa_a, canal_a):
        _criar_notif(empresa_a, canal_a)
        resp = admin_client.get(f"{BASE}/notificacoes/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_retrieve(self, admin_client, empresa_a, canal_a):
        n = _criar_notif(empresa_a, canal_a)
        resp = admin_client.get(f"{BASE}/notificacoes/{n.pk}/")
        assert resp.status_code == 200

    def test_filtro_por_status(self, admin_client, empresa_a, canal_a):
        _criar_notif(empresa_a, canal_a)
        resp = admin_client.get(f"{BASE}/notificacoes/?status=PENDENTE")
        assert resp.status_code == 200
        for r in resp.json()["results"]:
            assert r["status"] == "PENDENTE"

    def test_reenviar_status_falhou(self, admin_client, empresa_a, canal_a, settings):
        settings.WHATSAPP_PROVIDER = "FAKE"
        n = _criar_notif(empresa_a, canal_a)
        n.status = Notificacao.STATUS_FALHOU
        n.save()

        resp = admin_client.post(f"{BASE}/notificacoes/{n.pk}/reenviar/")
        assert resp.status_code == 200
        n.refresh_from_db()
        assert n.status == Notificacao.STATUS_PENDENTE

    def test_reenviar_status_enviada_retorna_400(self, admin_client, empresa_a, canal_a):
        n = _criar_notif(empresa_a, canal_a)
        n.status = Notificacao.STATUS_ENVIADA
        n.save()
        resp = admin_client.post(f"{BASE}/notificacoes/{n.pk}/reenviar/")
        assert resp.status_code == 400

    def test_viewer_nao_pode_reenviar(self, viewer_client, empresa_a, canal_a):
        n = _criar_notif(empresa_a, canal_a)
        n.status = Notificacao.STATUS_FALHOU
        n.save()
        resp = viewer_client.post(f"{BASE}/notificacoes/{n.pk}/reenviar/")
        assert resp.status_code == 403


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestDashboard:
    def test_dashboard_retorna_metricas(self, admin_client, empresa_a, canal_a):
        _criar_notif(empresa_a, canal_a)
        resp = admin_client.get(f"{BASE}/notificacoes/dashboard/")
        assert resp.status_code == 200
        data = resp.json()
        assert "notificacoes_pendentes" in data
        assert "enviadas_hoje" in data
        assert "entregues_hoje" in data
        assert "lidas_hoje" in data
        assert "falhas_hoje" in data
        assert "taxa_entrega" in data
        assert "taxa_leitura" in data

    def test_dashboard_viewer_pode_ver(self, viewer_client, empresa_a, canal_a):
        resp = viewer_client.get(f"{BASE}/notificacoes/dashboard/")
        assert resp.status_code == 200


# ──────────────────────────────────────────────
# Envio via API
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEnvioAPI:
    def test_enviar_cobranca_fiado(
        self,
        admin_client,
        empresa_a,
        canal_a,
        template_cobranca,
        conta_fiado_a,
        settings,
    ):
        settings.WHATSAPP_PROVIDER = "FAKE"
        resp = admin_client.post(
            f"{BASE}/whatsapp/enviar-cobranca-fiado/",
            {"conta_fiado_id": str(conta_fiado_a.pk)},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["tipo"] == "COBRANCA_FIADO"

    def test_enviar_confirmacao_pagamento(
        self,
        admin_client,
        empresa_a,
        canal_a,
        template_confirmacao,
        pagamento_fiado_a,
        settings,
    ):
        settings.WHATSAPP_PROVIDER = "FAKE"
        resp = admin_client.post(
            f"{BASE}/whatsapp/enviar-confirmacao-pagamento/",
            {"pagamento_fiado_id": str(pagamento_fiado_a.pk)},
            format="json",
        )
        assert resp.status_code == 201

    def test_enviar_cobranca_sem_canal_ativo_retorna_400(
        self, admin_client, empresa_a, canal_a, conta_fiado_a
    ):
        canal_a.ativo = False
        canal_a.save()
        resp = admin_client.post(
            f"{BASE}/whatsapp/enviar-cobranca-fiado/",
            {"conta_fiado_id": str(conta_fiado_a.pk)},
            format="json",
        )
        assert resp.status_code == 400

    def test_seller_pode_enviar_cobranca(
        self,
        seller_client,
        empresa_a,
        canal_a,
        template_cobranca,
        conta_fiado_a,
        settings,
    ):
        settings.WHATSAPP_PROVIDER = "FAKE"
        resp = seller_client.post(
            f"{BASE}/whatsapp/enviar-cobranca-fiado/",
            {"conta_fiado_id": str(conta_fiado_a.pk)},
            format="json",
        )
        assert resp.status_code in (201, 200)

    def test_viewer_nao_pode_enviar_cobranca(
        self, viewer_client, conta_fiado_a
    ):
        resp = viewer_client.post(
            f"{BASE}/whatsapp/enviar-cobranca-fiado/",
            {"conta_fiado_id": str(conta_fiado_a.pk)},
            format="json",
        )
        assert resp.status_code == 403

    def test_anonimo_nao_pode_enviar_cobranca(self, anon_client, conta_fiado_a):
        resp = anon_client.post(
            f"{BASE}/whatsapp/enviar-cobranca-fiado/",
            {"conta_fiado_id": str(conta_fiado_a.pk)},
            format="json",
        )
        assert resp.status_code == 401
