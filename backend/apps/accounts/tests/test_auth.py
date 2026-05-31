"""Tests for JWT auth endpoints: token obtain, refresh, verify, logout flow."""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

TOKEN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
VERIFY_URL = "/api/v1/auth/token/verify/"
ME_URL = "/api/v1/auth/me/"


# ── Token obtain ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenObtain:
    def test_valid_credentials_return_tokens(self, admin_alpha):
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": admin_alpha.email, "password": "testpass123"}, format="json")
        assert r.status_code == 200
        assert "access" in r.data
        assert "refresh" in r.data

    def test_wrong_password_returns_401(self, admin_alpha):
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": admin_alpha.email, "password": "wrong"}, format="json")
        assert r.status_code == 401

    def test_nonexistent_email_returns_401(self):
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": "nobody@x.com", "password": "pass"}, format="json")
        assert r.status_code == 401

    def test_missing_password_returns_400(self, admin_alpha):
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": admin_alpha.email}, format="json")
        assert r.status_code == 400

    def test_missing_email_returns_400(self):
        client = APIClient()
        r = client.post(TOKEN_URL, {"password": "testpass123"}, format="json")
        assert r.status_code == 400

    def test_inactive_user_cannot_login(self, admin_alpha):
        admin_alpha.is_active = False
        admin_alpha.save(update_fields=["is_active"])
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": admin_alpha.email, "password": "testpass123"}, format="json")
        assert r.status_code == 401

    def test_soft_deleted_user_cannot_login(self, admin_alpha):
        """Soft-deleted users have is_active=False so JWT rejects them."""
        admin_alpha.soft_delete()
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": admin_alpha.email, "password": "testpass123"}, format="json")
        assert r.status_code == 401

    def test_error_response_uses_envelope(self, admin_alpha):
        client = APIClient()
        r = client.post(TOKEN_URL, {"email": admin_alpha.email, "password": "wrong"}, format="json")
        assert r.status_code == 401
        assert r.data["error"] is True
        assert "status_code" in r.data
        assert "detail" in r.data


# ── Token refresh ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenRefresh:
    def test_valid_refresh_returns_new_access(self, admin_alpha):
        refresh = RefreshToken.for_user(admin_alpha)
        client = APIClient()
        r = client.post(REFRESH_URL, {"refresh": str(refresh)}, format="json")
        assert r.status_code == 200
        assert "access" in r.data

    def test_invalid_token_returns_401(self):
        client = APIClient()
        r = client.post(REFRESH_URL, {"refresh": "notavalidtoken"}, format="json")
        assert r.status_code == 401

    def test_missing_refresh_returns_400(self):
        client = APIClient()
        r = client.post(REFRESH_URL, {}, format="json")
        assert r.status_code == 400


# ── Token verify ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenVerify:
    def test_valid_access_token_returns_200(self, admin_alpha):
        refresh = RefreshToken.for_user(admin_alpha)
        client = APIClient()
        r = client.post(VERIFY_URL, {"token": str(refresh.access_token)}, format="json")
        assert r.status_code == 200

    def test_invalid_token_returns_401(self):
        client = APIClient()
        r = client.post(VERIFY_URL, {"token": "garbage"}, format="json")
        assert r.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMeEndpoint:
    def test_authenticated_returns_user_data(self, admin_alpha_client, admin_alpha):
        r = admin_alpha_client.get(ME_URL)
        assert r.status_code == 200
        assert r.data["email"] == admin_alpha.email
        assert r.data["role"] == User.ROLE_ADMIN

    def test_response_includes_company_id(self, admin_alpha_client, admin_alpha):
        r = admin_alpha_client.get(ME_URL)
        assert r.status_code == 200
        assert str(admin_alpha.company_id) == r.data["company_id"]

    def test_password_not_in_response(self, admin_alpha_client):
        r = admin_alpha_client.get(ME_URL)
        assert "password" not in r.data

    def test_unauthenticated_returns_401(self, anon_client):
        r = anon_client.get(ME_URL)
        assert r.status_code == 401


# ── Change password ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:
    CHANGE_URL = "/api/v1/auth/change-password/"

    def test_valid_change_succeeds(self, admin_alpha_client, admin_alpha):
        r = admin_alpha_client.post(
            self.CHANGE_URL,
            {"old_password": "testpass123", "new_password": "newpass456"},
            format="json",
        )
        assert r.status_code == 200
        admin_alpha.refresh_from_db()
        assert admin_alpha.check_password("newpass456")

    def test_wrong_old_password_returns_400(self, admin_alpha_client):
        r = admin_alpha_client.post(
            self.CHANGE_URL,
            {"old_password": "wrongpass", "new_password": "newpass456"},
            format="json",
        )
        assert r.status_code == 400

    def test_new_password_too_short_returns_400(self, admin_alpha_client):
        r = admin_alpha_client.post(
            self.CHANGE_URL,
            {"old_password": "testpass123", "new_password": "short"},
            format="json",
        )
        assert r.status_code == 400

    def test_unauthenticated_returns_401(self, anon_client):
        r = anon_client.post(
            self.CHANGE_URL,
            {"old_password": "testpass123", "new_password": "newpass456"},
            format="json",
        )
        assert r.status_code == 401
