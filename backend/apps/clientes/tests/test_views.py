from decimal import Decimal

import pytest
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.core.models import AuditLog
from .conftest import VALID_CPF_1, VALID_CPF_2, VALID_CNPJ_1, COMPANY_A, make_cliente

LIST_URL = "/api/v1/clientes/"


def detail_url(pk):
    return f"/api/v1/clientes/{pk}/"


def action_url(pk, action):
    return f"/api/v1/clientes/{pk}/{action}/"


def _create_payload(**kwargs):
    return {
        "nome": "Pedro Alves",
        "tipo_pessoa": "PF",
        "cpf_cnpj": VALID_CPF_2,
        "telefone": "11988880001",
        "email": "pedro@test.com",
        "cidade": "Rio de Janeiro",
        "estado": "RJ",
        "limite_credito": "2000.00",
        **kwargs,
    }


# ── LIST ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClienteList:
    def test_requires_auth(self, anon_client):
        r = anon_client.get(LIST_URL)
        assert r.status_code == 401

    def test_viewer_can_list(self, viewer_client, cliente):
        r = viewer_client.get(LIST_URL)
        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_pagination_envelope(self, admin_client, cliente):
        r = admin_client.get(LIST_URL)
        assert r.status_code == 200
        for key in ("count", "next", "previous", "total_pages", "current_page", "results"):
            assert key in r.data

    def test_excludes_soft_deleted(self, admin_client, cliente):
        cliente.soft_delete()
        r = admin_client.get(LIST_URL)
        assert r.data["count"] == 0

    def test_tenant_isolation(self, admin_client, cliente, cliente_outra_empresa):
        r = admin_client.get(LIST_URL)
        ids = [c["id"] for c in r.data["results"]]
        assert str(cliente.pk) in ids
        assert str(cliente_outra_empresa.pk) not in ids

    def test_search_by_nome(self, admin_client, cliente):
        r = admin_client.get(LIST_URL + "?search=João")
        assert r.data["count"] == 1

    def test_search_no_result(self, admin_client, cliente):
        r = admin_client.get(LIST_URL + "?search=xyz_nobody")
        assert r.data["count"] == 0

    def test_filter_bloqueado(self, admin_client, cliente, cliente_bloqueado):
        r = admin_client.get(LIST_URL + "?bloqueado=true")
        assert r.data["count"] == 1
        assert r.data["results"][0]["bloqueado"] is True

    def test_ordering(self, admin_client, cliente, cliente_bloqueado):
        r = admin_client.get(LIST_URL + "?ordering=-nome")
        names = [c["nome"] for c in r.data["results"]]
        assert names == sorted(names, reverse=True)

    def test_default_ordering_alfabetico(self, admin_client, empresa_a):
        for index, nome in enumerate(["Pedro", "Ana", "Maria", "Bruno", "Carlos"], start=1):
            make_cliente(empresa=empresa_a, nome=nome, cpf_cnpj=f"1000000000{index}")

        r = admin_client.get(LIST_URL)
        names = [c["nome"] for c in r.data["results"]]

        assert names == ["Ana", "Bruno", "Carlos", "Maria", "Pedro"]

    def test_search_mantem_ordem_alfabetica(self, admin_client, empresa_a):
        for index, nome in enumerate(["José", "Maria", "João", "Joaquim"], start=1):
            make_cliente(
                empresa=empresa_a,
                nome=nome,
                cpf_cnpj=f"2000000000{index}",
                email=f"cliente{index}@test.com",
            )

        r = admin_client.get(LIST_URL + "?search=jo")
        names = [c["nome"] for c in r.data["results"]]

        assert names == ["Joaquim", "José", "João"]

    def test_page_size(self, admin_client, cliente, cliente_bloqueado, cliente_inadimplente):
        r = admin_client.get(LIST_URL + "?page_size=1")
        assert len(r.data["results"]) == 1
        assert r.data["total_pages"] == 3


# ── CREATE ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClienteCreate:
    def test_seller_can_create(self, seller_client):
        r = seller_client.post(LIST_URL, data=_create_payload(), format="json")
        assert r.status_code == 201
        assert r.data["cpf_cnpj"] == VALID_CPF_2

    def test_viewer_cannot_create(self, viewer_client):
        r = viewer_client.post(LIST_URL, data=_create_payload(), format="json")
        assert r.status_code == 403

    def test_anon_cannot_create(self, anon_client):
        r = anon_client.post(LIST_URL, data=_create_payload(), format="json")
        assert r.status_code == 401

    def test_invalid_cpf_returns_400(self, admin_client):
        r = admin_client.post(LIST_URL, data=_create_payload(cpf_cnpj="00000000000"), format="json")
        assert r.status_code == 400
        assert "cpf_cnpj" in str(r.data)

    def test_invalid_cnpj_returns_400(self, admin_client):
        r = admin_client.post(
            LIST_URL,
            data=_create_payload(tipo_pessoa="PJ", cpf_cnpj="00000000000000"),
            format="json",
        )
        assert r.status_code == 400

    def test_duplicate_cpf_returns_400(self, admin_client, cliente):
        r = admin_client.post(LIST_URL, data=_create_payload(cpf_cnpj=VALID_CPF_1), format="json")
        assert r.status_code == 400

    def test_missing_required_fields(self, admin_client):
        r = admin_client.post(LIST_URL, data={}, format="json")
        assert r.status_code == 400

    def test_response_uses_detail_serializer(self, admin_client):
        r = admin_client.post(LIST_URL, data=_create_payload(), format="json")
        assert r.status_code == 201
        for field in ("id", "nome", "cpf_cnpj", "saldo_devedor", "credito_disponivel"):
            assert field in r.data

    def test_creates_audit_log(self, admin_client, admin_user):
        r = admin_client.post(LIST_URL, data=_create_payload(), format="json")
        assert r.status_code == 201
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            action=AuditLog.ACTION_CREATE,
        ).first()
        assert log is not None

    def test_pj_with_cnpj(self, admin_client):
        r = admin_client.post(
            LIST_URL,
            data=_create_payload(tipo_pessoa="PJ", cpf_cnpj=VALID_CNPJ_1),
            format="json",
        )
        assert r.status_code == 201
        assert r.data["tipo_pessoa"] == "PJ"


# ── RETRIEVE ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClienteRetrieve:
    def test_viewer_can_retrieve(self, viewer_client, cliente):
        r = viewer_client.get(detail_url(cliente.pk))
        assert r.status_code == 200
        assert r.data["id"] == str(cliente.pk)

    def test_wrong_company_returns_404(self, other_company_client, cliente):
        r = other_company_client.get(detail_url(cliente.pk))
        assert r.status_code == 404

    def test_soft_deleted_returns_404(self, admin_client, cliente):
        cliente.soft_delete()
        r = admin_client.get(detail_url(cliente.pk))
        assert r.status_code == 404

    def test_detail_has_address_fields(self, admin_client, cliente):
        r = admin_client.get(detail_url(cliente.pk))
        for field in ("cep", "rua", "bairro", "complemento", "observacao"):
            assert field in r.data


# ── PARTIAL UPDATE ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClienteUpdate:
    def test_manager_can_update(self, manager_client, cliente):
        r = manager_client.patch(
            detail_url(cliente.pk),
            data={"nome": "Novo Nome"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["nome"] == "Novo Nome"

    def test_seller_cannot_update(self, seller_client, cliente):
        r = seller_client.patch(
            detail_url(cliente.pk),
            data={"nome": "Novo Nome"},
            format="json",
        )
        assert r.status_code == 403

    def test_viewer_cannot_update(self, viewer_client, cliente):
        r = viewer_client.patch(
            detail_url(cliente.pk),
            data={"nome": "X"},
            format="json",
        )
        assert r.status_code == 403

    def test_update_invalid_cpf_returns_400(self, manager_client, cliente):
        r = manager_client.patch(
            detail_url(cliente.pk),
            data={"cpf_cnpj": "00000000000"},
            format="json",
        )
        assert r.status_code == 400

    def test_update_creates_audit_log(self, admin_client, cliente):
        admin_client.patch(
            detail_url(cliente.pk),
            data={"nome": "Atualizado"},
            format="json",
        )
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=cliente.pk,
            action=AuditLog.ACTION_UPDATE,
        ).first()
        assert log is not None
        assert log.before["nome"] == "João da Silva"


# ── DESTROY ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClienteDestroy:
    def test_admin_can_delete(self, admin_client, cliente):
        r = admin_client.delete(detail_url(cliente.pk))
        assert r.status_code == 204
        cliente.refresh_from_db()
        assert cliente.is_deleted is True

    def test_manager_cannot_delete(self, manager_client, cliente):
        r = manager_client.delete(detail_url(cliente.pk))
        assert r.status_code == 403

    def test_soft_delete_hides_from_list(self, admin_client, cliente):
        admin_client.delete(detail_url(cliente.pk))
        r = admin_client.get(LIST_URL)
        assert r.data["count"] == 0

    def test_soft_delete_creates_audit_log(self, admin_client, cliente):
        admin_client.delete(detail_url(cliente.pk))
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=cliente.pk,
            action=AuditLog.ACTION_DELETE,
        ).first()
        assert log is not None


# ── CUSTOM ACTIONS ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClienteInadimplentes:
    def test_returns_only_inadimplentes(self, admin_client, cliente, cliente_inadimplente):
        r = admin_client.get(LIST_URL + "inadimplentes/")
        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_viewer_can_access(self, viewer_client, cliente_inadimplente):
        r = viewer_client.get(LIST_URL + "inadimplentes/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestClienteBloqueados:
    def test_returns_only_bloqueados(self, admin_client, cliente, cliente_bloqueado):
        r = admin_client.get(LIST_URL + "bloqueados/")
        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_viewer_can_access(self, viewer_client, cliente_bloqueado):
        r = viewer_client.get(LIST_URL + "bloqueados/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestBloquearAction:
    def test_manager_can_bloquear(self, manager_client, cliente):
        r = manager_client.post(action_url(cliente.pk, "bloquear"))
        assert r.status_code == 200
        assert r.data["bloqueado"] is True

    def test_seller_cannot_bloquear(self, seller_client, cliente):
        r = seller_client.post(action_url(cliente.pk, "bloquear"))
        assert r.status_code == 403

    def test_bloquear_already_blocked_returns_400(self, admin_client, cliente_bloqueado):
        r = admin_client.post(action_url(cliente_bloqueado.pk, "bloquear"))
        assert r.status_code == 400

    def test_desbloquear_manager_can(self, manager_client, cliente_bloqueado):
        r = manager_client.post(action_url(cliente_bloqueado.pk, "desbloquear"))
        assert r.status_code == 200
        assert r.data["bloqueado"] is False

    def test_desbloquear_not_blocked_returns_400(self, admin_client, cliente):
        r = admin_client.post(action_url(cliente.pk, "desbloquear"))
        assert r.status_code == 400
