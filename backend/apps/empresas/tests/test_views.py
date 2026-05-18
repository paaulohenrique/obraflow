import pytest

from apps.empresas.models import Empresa
from .conftest import VALID_CNPJ_A, VALID_CNPJ_B, VALID_CNPJ_C

LIST_URL = "/api/v1/empresas/"


def detail_url(pk):
    return f"/api/v1/empresas/{pk}/"


def _payload(**kwargs):
    return {
        "razao_social": "Nova Empresa LTDA",
        "cnpj": VALID_CNPJ_C,
        "plano": "basico",
        "limite_usuarios": 5,
        **kwargs,
    }


# ── LIST ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmpresaList:
    def test_requires_auth(self, anon_client):
        assert anon_client.get(LIST_URL).status_code == 401

    def test_authenticated_user_can_list(self, regular_client, empresa_alpha):
        r = regular_client.get(LIST_URL)
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_pagination_envelope(self, super_client, empresa_alpha):
        r = super_client.get(LIST_URL)
        assert r.status_code == 200
        for key in ("count", "next", "previous", "total_pages", "current_page", "results"):
            assert key in r.data


# ── CREATE ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmpresaCreate:
    def test_superuser_can_create(self, super_client):
        r = super_client.post(LIST_URL, data=_payload(), format="json")
        assert r.status_code == 201
        assert r.data["cnpj"] == VALID_CNPJ_C

    def test_regular_admin_cannot_create(self, regular_client):
        r = regular_client.post(LIST_URL, data=_payload(), format="json")
        assert r.status_code == 403

    def test_anon_cannot_create(self, anon_client):
        r = anon_client.post(LIST_URL, data=_payload(), format="json")
        assert r.status_code == 401

    def test_invalid_cnpj_returns_400(self, super_client):
        r = super_client.post(LIST_URL, data=_payload(cnpj="00000000000000"), format="json")
        assert r.status_code == 400
        assert "cnpj" in str(r.data)

    def test_duplicate_cnpj_returns_400(self, super_client, empresa_alpha):
        r = super_client.post(LIST_URL, data=_payload(cnpj=VALID_CNPJ_A), format="json")
        assert r.status_code == 400

    def test_missing_razao_social_returns_400(self, super_client):
        r = super_client.post(LIST_URL, data={"cnpj": VALID_CNPJ_C}, format="json")
        assert r.status_code == 400

    def test_response_has_detail_fields(self, super_client):
        r = super_client.post(LIST_URL, data=_payload(), format="json")
        assert r.status_code == 201
        for f in ("id", "razao_social", "cnpj", "plano", "total_usuarios"):
            assert f in r.data


# ── RETRIEVE ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmpresaRetrieve:
    def test_superuser_can_retrieve_any(self, super_client, empresa_alpha, empresa_beta):
        r = super_client.get(detail_url(empresa_beta.pk))
        assert r.status_code == 200

    def test_not_found(self, super_client):
        import uuid
        r = super_client.get(detail_url(uuid.uuid4()))
        assert r.status_code == 404

    def test_malformed_uuid(self, super_client):
        r = super_client.get(detail_url("not-a-uuid"))
        assert r.status_code == 404

    def test_total_usuarios_count(self, super_client, empresa_alpha, superuser):
        r = super_client.get(detail_url(empresa_alpha.pk))
        assert r.status_code == 200
        assert r.data["total_usuarios"] >= 1


# ── UPDATE ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmpresaUpdate:
    def test_superuser_can_update(self, super_client, empresa_alpha):
        r = super_client.patch(
            detail_url(empresa_alpha.pk),
            data={"nome_fantasia": "Alpha Store"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["nome_fantasia"] == "Alpha Store"

    def test_regular_admin_cannot_update(self, regular_client, empresa_alpha):
        r = regular_client.patch(
            detail_url(empresa_alpha.pk),
            data={"nome_fantasia": "X"},
            format="json",
        )
        assert r.status_code == 403


# ── DESTROY ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmpresaDestroy:
    def test_superuser_can_delete(self, super_client, empresa_beta):
        r = super_client.delete(detail_url(empresa_beta.pk))
        assert r.status_code == 204
        empresa_beta.refresh_from_db()
        assert empresa_beta.is_deleted is True

    def test_regular_admin_cannot_delete(self, regular_client, empresa_alpha):
        r = regular_client.delete(detail_url(empresa_alpha.pk))
        assert r.status_code == 403


# ── MULTI-TENANT ISOLATION ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestMultiTenantIsolation:
    def test_user_company_fk_set_correctly(self, regular_admin, empresa_alpha):
        assert regular_admin.company_id == empresa_alpha.pk
        assert regular_admin.company == empresa_alpha

    def test_clientes_scoped_to_company(self, empresa_alpha, empresa_beta):
        from apps.clientes.models import Cliente
        from apps.clientes.selectors import get_clientes_ativos

        Cliente.objects.create(
            company=empresa_alpha,
            nome="Cliente Alpha",
            tipo_pessoa="PF",
            cpf_cnpj="52998224725",
        )
        Client_beta = Cliente.objects.create(
            company=empresa_beta,
            nome="Cliente Beta",
            tipo_pessoa="PF",
            cpf_cnpj="52998224725",  # same CPF, different company → allowed
        )

        qs_a = get_clientes_ativos(company_id=empresa_alpha.pk)
        qs_b = get_clientes_ativos(company_id=empresa_beta.pk)

        assert qs_a.count() == 1
        assert qs_b.count() == 1
        assert qs_a.first().company == empresa_alpha
        assert Client_beta in qs_b
