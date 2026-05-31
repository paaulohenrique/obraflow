"""Tests for user management: list, create, soft-delete, multi-tenant isolation.

UserListView and UserCreateView require is_staff=True (IsAdminUser).
Company-level user management is done via platform superusers only.
Regular ROLE_ADMIN users without is_staff get 403.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

LIST_URL = "/api/v1/auth/users/"
CREATE_URL = "/api/v1/auth/users/create/"


# ── User list ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserList:
    def test_superuser_can_list_own_company_users(
        self, super_client, superuser, admin_alpha, manager_alpha
    ):
        r = super_client.get(LIST_URL)
        assert r.status_code == 200
        emails = [u["email"] for u in r.data["results"]]
        assert admin_alpha.email in emails
        assert manager_alpha.email in emails

    def test_users_from_other_company_not_visible(
        self, super_client, admin_beta
    ):
        """Superuser is scoped to empresa_alpha; admin_beta is in empresa_beta."""
        r = super_client.get(LIST_URL)
        emails = [u["email"] for u in r.data["results"]]
        assert admin_beta.email not in emails

    def test_regular_admin_role_cannot_list_users(self, admin_alpha_client):
        """ROLE_ADMIN without is_staff gets 403."""
        r = admin_alpha_client.get(LIST_URL)
        assert r.status_code == 403

    def test_manager_cannot_list_users(self, manager_alpha_client):
        r = manager_alpha_client.get(LIST_URL)
        assert r.status_code == 403

    def test_unauthenticated_cannot_list(self, anon_client):
        r = anon_client.get(LIST_URL)
        assert r.status_code == 401

    def test_response_does_not_expose_password(self, super_client, admin_alpha):
        r = super_client.get(LIST_URL)
        assert r.status_code == 200
        for user in r.data["results"]:
            assert "password" not in user

    def test_pagination_envelope_present(self, super_client):
        r = super_client.get(LIST_URL)
        assert r.status_code == 200
        for key in ("count", "results"):
            assert key in r.data


# ── User create ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserCreate:
    def _payload(self, **kwargs):
        return {
            "email": "new@alpha.com",
            "name": "Novo Usuário",
            "role": User.ROLE_SELLER,
            "password": "strongpass1",
            **kwargs,
        }

    def test_superuser_can_create_user(self, super_client, empresa_alpha):
        r = super_client.post(CREATE_URL, self._payload(), format="json")
        assert r.status_code == 201
        user = User.objects.filter(email="new@alpha.com").first()
        assert user is not None
        assert user.company_id == empresa_alpha.pk

    def test_created_user_inherits_creator_company(self, super_client, empresa_alpha):
        """company is injected from request.user.company by the view."""
        super_client.post(CREATE_URL, self._payload(), format="json")
        user = User.objects.filter(email="new@alpha.com").first()
        assert user.company_id == empresa_alpha.pk

    def test_regular_admin_cannot_create_user(self, admin_alpha_client):
        r = admin_alpha_client.post(CREATE_URL, self._payload(), format="json")
        assert r.status_code == 403

    def test_duplicate_email_returns_400(self, super_client, admin_alpha):
        r = super_client.post(
            CREATE_URL, self._payload(email=admin_alpha.email), format="json"
        )
        assert r.status_code == 400

    def test_invalid_role_returns_400(self, super_client):
        r = super_client.post(
            CREATE_URL, self._payload(role="supervillain"), format="json"
        )
        assert r.status_code == 400

    def test_password_too_short_returns_400(self, super_client):
        r = super_client.post(
            CREATE_URL, self._payload(password="short"), format="json"
        )
        assert r.status_code == 400

    def test_missing_email_returns_400(self, super_client):
        payload = self._payload()
        payload.pop("email")
        r = super_client.post(CREATE_URL, payload, format="json")
        assert r.status_code == 400

    def test_response_does_not_expose_password(self, super_client):
        r = super_client.post(CREATE_URL, self._payload(), format="json")
        assert r.status_code == 201
        assert "password" not in r.data

    def test_unauthenticated_cannot_create(self, anon_client):
        r = anon_client.post(CREATE_URL, self._payload(), format="json")
        assert r.status_code == 401


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserSoftDelete:
    def test_soft_deleted_user_is_inactive(self, seller_alpha):
        seller_alpha.soft_delete()
        seller_alpha.refresh_from_db()
        assert seller_alpha.is_active is False
        assert seller_alpha.deleted_at is not None
        assert seller_alpha.is_deleted is True

    def test_soft_deleted_user_cannot_login(self, seller_alpha):
        """Soft-deleted users have is_active=False; JWT rejects them."""
        seller_alpha.soft_delete()
        client = APIClient()
        r = client.post(
            "/api/v1/auth/token/",
            {"email": seller_alpha.email, "password": "testpass123"},
            format="json",
        )
        assert r.status_code == 401

    def test_restore_reactivates_user(self, seller_alpha):
        seller_alpha.soft_delete()
        seller_alpha.restore()
        seller_alpha.refresh_from_db()
        assert seller_alpha.is_active is True
        assert seller_alpha.deleted_at is None

    def test_is_deleted_property_before_delete(self, seller_alpha):
        assert seller_alpha.is_deleted is False

    def test_is_manager_property(self, manager_alpha):
        assert manager_alpha.is_manager is True

    def test_is_admin_property(self, admin_alpha):
        assert admin_alpha.is_admin is True

    def test_seller_is_not_manager(self, seller_alpha):
        assert seller_alpha.is_manager is False


# ── Multi-tenant isolation ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserMultiTenantIsolation:
    def test_superuser_sees_only_own_company_users(
        self, super_client, admin_alpha, manager_alpha, seller_alpha, viewer_alpha,
        admin_beta
    ):
        r = super_client.get(LIST_URL)
        assert r.status_code == 200
        emails = {u["email"] for u in r.data["results"]}
        # All alpha users visible
        for user in [admin_alpha, manager_alpha, seller_alpha, viewer_alpha]:
            assert user.email in emails
        # Beta user NOT visible
        assert admin_beta.email not in emails

    def test_all_listed_users_share_same_company(self, super_client, empresa_alpha):
        r = super_client.get(LIST_URL)
        for user in r.data["results"]:
            assert str(empresa_alpha.pk) == user["company_id"]
