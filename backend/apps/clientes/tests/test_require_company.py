"""
Tests for require_company guard applied to all clientes service functions.

Covers both API-level (HTTP 403) and service-level (PermissionDenied) paths.
"""
import pytest
from decimal import Decimal
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.services import (
    bloquear_cliente,
    desbloquear_cliente,
    soft_delete_cliente,
)
from .conftest import make_cliente, VALID_CPF_1, VALID_CPF_2


LIST_URL = "/api/v1/clientes/"


def _make_user_without_company(db):
    return User.objects.create_user(
        email="nocompany@test.com",
        name="Sem Empresa",
        password="testpass123",
        role=User.ROLE_ADMIN,
        company=None,
    )


def _auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ── API-level: all clientes endpoints return 403 ──────────────────────────────

@pytest.mark.django_db
class TestRequireCompanyViaAPI:
    @pytest.fixture
    def nocompany_client(self, db):
        user = _make_user_without_company(db)
        return _auth_client_for(user)

    def test_list_returns_403(self, nocompany_client):
        r = nocompany_client.get(LIST_URL)
        assert r.status_code == 403

    def test_create_returns_403(self, nocompany_client):
        r = nocompany_client.post(LIST_URL, {}, format="json")
        assert r.status_code == 403

    def test_403_uses_error_envelope(self, nocompany_client):
        r = nocompany_client.get(LIST_URL)
        assert r.data["error"] is True
        assert r.data["status_code"] == 403
        assert "empresa" in r.data["detail"].lower()

    def test_retrieve_returns_403(self, nocompany_client, empresa_a):
        cliente = make_cliente(empresa=empresa_a)
        r = nocompany_client.get(f"{LIST_URL}{cliente.pk}/")
        assert r.status_code == 403

    def test_bloquear_action_returns_403(self, nocompany_client, empresa_a):
        cliente = make_cliente(empresa=empresa_a)
        r = nocompany_client.post(f"{LIST_URL}{cliente.pk}/bloquear/")
        assert r.status_code == 403

    def test_desbloquear_action_returns_403(self, nocompany_client, empresa_a):
        cliente = make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_2, bloqueado=True)
        r = nocompany_client.post(f"{LIST_URL}{cliente.pk}/desbloquear/")
        assert r.status_code == 403

    def test_destroy_returns_403(self, nocompany_client, empresa_a):
        cliente = make_cliente(empresa=empresa_a)
        r = nocompany_client.delete(f"{LIST_URL}{cliente.pk}/")
        assert r.status_code == 403


# ── Service-level: direct calls raise PermissionDenied ───────────────────────

@pytest.mark.django_db
class TestRequireCompanyInServices:
    @pytest.fixture
    def nocompany_user(self, db):
        return _make_user_without_company(db)

    def test_soft_delete_raises_for_user_without_company(self, nocompany_user, empresa_a):
        cliente = make_cliente(empresa=empresa_a)
        with pytest.raises(PermissionDenied):
            soft_delete_cliente(user=nocompany_user, cliente=cliente)

    def test_bloquear_raises_for_user_without_company(self, nocompany_user, empresa_a):
        cliente = make_cliente(empresa=empresa_a)
        with pytest.raises(PermissionDenied):
            bloquear_cliente(user=nocompany_user, cliente=cliente)

    def test_desbloquear_raises_for_user_without_company(self, nocompany_user, empresa_a):
        cliente = make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_2, bloqueado=True)
        with pytest.raises(PermissionDenied):
            desbloquear_cliente(user=nocompany_user, cliente=cliente)

    def test_no_audit_log_created_when_company_missing(self, nocompany_user, empresa_a):
        from apps.core.models import AuditLog
        cliente = make_cliente(empresa=empresa_a)
        count_before = AuditLog.objects.filter(entity_type="Cliente").count()
        try:
            soft_delete_cliente(user=nocompany_user, cliente=cliente)
        except PermissionDenied:
            pass
        assert AuditLog.objects.filter(entity_type="Cliente").count() == count_before

    def test_cliente_not_modified_when_company_missing(self, nocompany_user, empresa_a):
        cliente = make_cliente(empresa=empresa_a)
        try:
            bloquear_cliente(user=nocompany_user, cliente=cliente)
        except PermissionDenied:
            pass
        cliente.refresh_from_db()
        assert cliente.bloqueado is False
