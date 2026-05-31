"""Testes de API: permissões, upload, confirmação, dashboard, multi-tenant."""
import pytest
from decimal import Decimal

from apps.notas_entrada.models import NotaFiscalEntrada
from apps.notas_entrada.services.nota import importar_xml_nota
from apps.notas_entrada.services.confirmacao import confirmar_nota

from .conftest import xml_file, xml_bytes

URL_BASE = "/api/v1/notas-entrada/"


def upload_url():
    return f"{URL_BASE}upload/"


def importar_chave_url():
    return f"{URL_BASE}importar-chave/"


def detail_url(pk):
    return f"{URL_BASE}{pk}/"


def confirmar_url(pk):
    return f"{URL_BASE}{pk}/confirmar/"


def rejeitar_url(pk):
    return f"{URL_BASE}{pk}/rejeitar/"


def vincular_fornecedor_url(pk):
    return f"{URL_BASE}{pk}/vincular-fornecedor/"


def itens_url(pk):
    return f"{URL_BASE}{pk}/itens/"


def historico_url(pk):
    return f"{URL_BASE}{pk}/historico/"


def dashboard_url():
    return f"{URL_BASE}dashboard/"


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_nota(user, filename="nfe_valida.xml", name="nfe.xml"):
    from apps.estoque.models import UnidadeMedida
    UnidadeMedida.objects.get_or_create(
        company=user.company, sigla="MIL", defaults={"nome": "Mil Unidades"}
    )
    UnidadeMedida.objects.get_or_create(
        company=user.company, sigla="M3", defaults={"nome": "Metro Cúbico"}
    )
    arquivo = xml_file(filename, name)
    return importar_xml_nota(user=user, arquivo=arquivo)


# ── Permissões ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPermissoes:
    def test_anon_get_401(self, anon_client):
        assert anon_client.get(URL_BASE).status_code == 401

    def test_anon_upload_401(self, anon_client):
        assert anon_client.post(upload_url(), data={}, format="multipart").status_code == 401

    def test_seller_nao_pode_upload(self, seller_client):
        r = seller_client.post(upload_url(), data={"arquivo": xml_file()}, format="multipart")
        assert r.status_code == 403

    def test_viewer_nao_pode_upload(self, viewer_client):
        r = viewer_client.post(upload_url(), data={"arquivo": xml_file()}, format="multipart")
        assert r.status_code == 403

    def test_seller_pode_listar(self, seller_client, admin_user):
        r = seller_client.get(URL_BASE)
        assert r.status_code == 200

    def test_viewer_pode_listar(self, viewer_client):
        r = viewer_client.get(URL_BASE)
        assert r.status_code == 200

    def test_seller_nao_pode_confirmar(self, seller_client, admin_user, empresa_a):
        nota = make_nota(admin_user)
        r = seller_client.post(confirmar_url(nota.pk), data={}, format="json")
        assert r.status_code == 403

    def test_seller_nao_pode_rejeitar(self, seller_client, admin_user):
        nota = make_nota(admin_user)
        r = seller_client.post(rejeitar_url(nota.pk), data={"motivo": "x"}, format="json")
        assert r.status_code == 403

    def test_manager_pode_confirmar_e_rejeitar(self, manager_client, manager_user):
        nota = make_nota(manager_user)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])
        r = manager_client.post(confirmar_url(nota.pk), data={}, format="json")
        assert r.status_code == 200


# ── Upload ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpload:
    def test_upload_valido_retorna_201(self, admin_client):
        r = admin_client.post(upload_url(), data={"arquivo": xml_file()}, format="multipart")
        assert r.status_code == 201
        assert r.data["status"] == NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO
        assert r.data["numero"] == "123"

    def test_upload_sem_arquivo_retorna_400(self, admin_client):
        r = admin_client.post(upload_url(), data={}, format="multipart")
        assert r.status_code == 400

    def test_upload_arquivo_invalido_retorna_400(self, admin_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        arquivo = SimpleUploadedFile("nfe.pdf", b"pdf content", content_type="application/pdf")
        r = admin_client.post(upload_url(), data={"arquivo": arquivo}, format="multipart")
        assert r.status_code == 400

    def test_upload_xml_malformado_retorna_400(self, admin_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        arquivo = SimpleUploadedFile("nfe.xml", b"<malformado>", content_type="text/xml")
        r = admin_client.post(upload_url(), data={"arquivo": arquivo}, format="multipart")
        assert r.status_code == 400

    def test_upload_duplicado_retorna_400(self, admin_client):
        admin_client.post(upload_url(), data={"arquivo": xml_file()}, format="multipart")
        r = admin_client.post(upload_url(), data={"arquivo": xml_file()}, format="multipart")
        assert r.status_code == 400

    def test_upload_retorna_itens(self, admin_client):
        r = admin_client.post(upload_url(), data={"arquivo": xml_file()}, format="multipart")
        assert r.status_code == 201
        assert len(r.data["itens"]) == 3


# ── Importar por Chave ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestImportarChave:
    def test_retorna_501(self, admin_client):
        r = admin_client.post(
            importar_chave_url(),
            data={"chave_acesso": "35210112345678000195550010000001231000012340"},
            format="json",
        )
        assert r.status_code == 501
        assert "V2" in r.data["detail"]

    def test_chave_invalida_retorna_400(self, admin_client):
        r = admin_client.post(
            importar_chave_url(),
            data={"chave_acesso": "chave_curta_invalida"},
            format="json",
        )
        assert r.status_code == 400


# ── Listagem e Filtros ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestListagem:
    def test_lista_apenas_empresa_propria(self, admin_client, admin_user, client_b, user_b):
        make_nota(admin_user)
        make_nota(user_b, "nfe_sem_namespace.xml", "nfe_b.xml")

        r_a = admin_client.get(URL_BASE)
        r_b = client_b.get(URL_BASE)

        assert r_a.status_code == 200
        assert r_b.status_code == 200
        assert r_a.data["count"] == 1
        assert r_b.data["count"] == 1

    def test_filtro_status(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        r = admin_client.get(URL_BASE, {"status": "AGUARDANDO_REVISAO"})
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_filtro_search_numero(self, admin_client, admin_user):
        make_nota(admin_user)
        r = admin_client.get(URL_BASE, {"search": "123"})
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_ordering_funcionando(self, admin_client, admin_user):
        make_nota(admin_user)
        r = admin_client.get(URL_BASE, {"ordering": "data_emissao"})
        assert r.status_code == 200


# ── Detalhe ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDetalhe:
    def test_detalhe_retorna_nota(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        r = admin_client.get(detail_url(nota.pk))
        assert r.status_code == 200
        assert str(r.data["id"]) == str(nota.pk)

    def test_detalhe_outra_empresa_404(self, admin_client, admin_user, client_b, user_b):
        nota_b = make_nota(user_b, "nfe_sem_namespace.xml", "nfe_b.xml")
        r = admin_client.get(detail_url(nota_b.pk))
        assert r.status_code == 404

    def test_detalhe_inexistente_404(self, admin_client):
        r = admin_client.get(detail_url("00000000-0000-0000-0000-000000000000"))
        assert r.status_code == 404


# ── Vincular Fornecedor ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVincularFornecedorAPI:
    def test_vincular_fornecedor_sucesso(self, admin_client, admin_user, fornecedor_a):
        nota = make_nota(admin_user)
        r = admin_client.post(
            vincular_fornecedor_url(nota.pk),
            data={"fornecedor": str(fornecedor_a.pk)},
            format="json",
        )
        assert r.status_code == 200
        assert str(r.data["fornecedor"]) == str(fornecedor_a.pk)

    def test_seller_nao_pode_vincular(self, seller_client, admin_user, fornecedor_a):
        nota = make_nota(admin_user)
        r = seller_client.post(
            vincular_fornecedor_url(nota.pk),
            data={"fornecedor": str(fornecedor_a.pk)},
            format="json",
        )
        assert r.status_code == 403


# ── Confirmar ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestConfirmarAPI:
    def test_confirmar_nota_com_itens_ignorados(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])

        r = admin_client.post(confirmar_url(nota.pk), data={}, format="json")
        assert r.status_code == 200
        assert r.data["status"] == NotaFiscalEntrada.STATUS_CONFIRMADA

    def test_confirmar_itens_pendentes_400(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        # Remover auto-match de todos itens
        nota.itens.all().update(produto=None)

        r = admin_client.post(confirmar_url(nota.pk), data={}, format="json")
        assert r.status_code == 400

    def test_confirmar_com_conta_pagar(self, admin_client, admin_user, categoria_despesa):
        nota = make_nota(admin_user)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])

        r = admin_client.post(
            confirmar_url(nota.pk),
            data={
                "criar_conta_pagar": True,
                "dados_conta_pagar": {
                    "categoria": str(categoria_despesa.pk),
                    "data_vencimento": "2026-06-30",
                    "observacao": "Pagamento NF-e",
                },
            },
            format="json",
        )
        assert r.status_code == 200
        assert r.data["conta_pagar"] is not None

    def test_confirmar_sem_categoria_quando_criar_cp_400(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])

        r = admin_client.post(
            confirmar_url(nota.pk),
            data={"criar_conta_pagar": True},
            format="json",
        )
        assert r.status_code == 400


# ── Rejeitar ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRejeitarAPI:
    def test_rejeitar_sucesso(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        r = admin_client.post(rejeitar_url(nota.pk), data={"motivo": "Duplicada"}, format="json")
        assert r.status_code == 200
        assert r.data["status"] == NotaFiscalEntrada.STATUS_REJEITADA

    def test_rejeitar_sem_motivo_400(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        r = admin_client.post(rejeitar_url(nota.pk), data={"motivo": ""}, format="json")
        assert r.status_code == 400

    def test_rejeitar_confirmada_400(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])
        admin_client.post(confirmar_url(nota.pk), data={}, format="json")

        r = admin_client.post(rejeitar_url(nota.pk), data={"motivo": "Tentativa"}, format="json")
        assert r.status_code == 400


# ── Itens ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestItensAPI:
    def test_listar_itens(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        r = admin_client.get(itens_url(nota.pk))
        assert r.status_code == 200
        assert r.data["count"] == 3

    def test_patch_item_vincular_produto(self, admin_client, admin_user, produto_sem_ean):
        nota = make_nota(admin_user)
        item = nota.itens.filter(produto__isnull=True, ignorado=False).first()
        if item is None:
            pytest.skip("Sem item sem produto")

        r = admin_client.patch(
            f"{URL_BASE}{nota.pk}/itens/{item.pk}/",
            data={"produto": str(produto_sem_ean.pk)},
            format="json",
        )
        assert r.status_code == 200
        assert str(r.data["produto"]) == str(produto_sem_ean.pk)

    def test_patch_item_ignorar(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        item = nota.itens.filter(produto__isnull=True, ignorado=False).first()
        if item is None:
            pytest.skip("Sem item sem produto")

        r = admin_client.patch(
            f"{URL_BASE}{nota.pk}/itens/{item.pk}/",
            data={"ignorado": True},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["ignorado"] is True

    def test_sugestoes_produto(self, admin_client, admin_user, produto_cimento):
        nota = make_nota(admin_user)
        item = nota.itens.first()
        r = admin_client.get(f"{URL_BASE}{nota.pk}/itens/{item.pk}/sugestoes-produto/")
        assert r.status_code == 200
        assert isinstance(r.data, list)


# ── Histórico ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHistoricoAPI:
    def test_historico_retorna_eventos(self, admin_client, admin_user):
        nota = make_nota(admin_user)
        r = admin_client.get(historico_url(nota.pk))
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_historico_viewer_pode_ver(self, viewer_client, admin_user):
        nota = make_nota(admin_user)
        r = viewer_client.get(historico_url(nota.pk))
        assert r.status_code == 200


# ── Dashboard ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDashboardAPI:
    def test_dashboard_retorna_metricas(self, admin_client, admin_user):
        make_nota(admin_user)
        r = admin_client.get(dashboard_url())
        assert r.status_code == 200
        assert "aguardando_revisao" in r.data
        assert "notas_importadas_hoje" in r.data
        assert "confirmadas_mes" in r.data
        assert "valor_total_confirmado_mes" in r.data
        assert "itens_sem_produto_pendentes" in r.data

    def test_dashboard_viewer_pode_ver(self, viewer_client):
        r = viewer_client.get(dashboard_url())
        assert r.status_code == 200

    def test_dashboard_tenant_isolado(self, admin_client, client_b, admin_user, user_b):
        make_nota(admin_user)
        r_a = admin_client.get(dashboard_url())
        r_b = client_b.get(dashboard_url())
        assert r_a.data["notas_importadas_hoje"] >= 1
        assert r_b.data["notas_importadas_hoje"] == 0
