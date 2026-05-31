"""
Tests for LoginRateThrottle.

The throttle is controlled exclusively by the presence of "login" in
DEFAULT_THROTTLE_RATES — NOT by DEFAULT_THROTTLE_CLASSES. These tests
verify both the active and inactive cases, using an in-memory cache with
a unique location per test to guarantee isolation.
"""
import uuid
import pytest
from rest_framework.test import APIClient

LOGIN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"

# ── Reusable settings blocks ──────────────────────────────────────────────────

_BASE_REST = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# Throttle ON: "login" key present in THROTTLE_RATES.
# DEFAULT_THROTTLE_CLASSES is intentionally empty to prove independence.
_THROTTLE_ON = {
    **_BASE_REST,
    "DEFAULT_THROTTLE_CLASSES": [],       # ← empty on purpose
    "DEFAULT_THROTTLE_RATES": {"login": "5/min"},
}

# Throttle OFF: "login" key absent from THROTTLE_RATES.
_THROTTLE_OFF = {
    **_BASE_REST,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {},  # ← no "login" key → throttle disabled
}


@pytest.fixture
def throttle_on(settings):
    """Active throttle with a fresh isolated in-memory cache."""
    settings.REST_FRAMEWORK = _THROTTLE_ON
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"throttle-on-{uuid.uuid4()}",
        }
    }
    return settings


@pytest.fixture
def throttle_off(settings):
    """Throttle disabled — login key absent from THROTTLE_RATES."""
    settings.REST_FRAMEWORK = _THROTTLE_OFF
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"throttle-off-{uuid.uuid4()}",
        }
    }
    return settings


def _post(client, email="x@x.com", password="wrong"):
    return client.post(
        LOGIN_URL,
        data={"email": email, "password": password},
        format="json",
    )


# ── Throttle ACTIVE ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_first_five_attempts_not_throttled(throttle_on):
    client = APIClient()
    for i in range(5):
        r = _post(client)
        assert r.status_code != 429, f"Throttled too early on attempt {i + 1}"


@pytest.mark.django_db
def test_sixth_attempt_is_throttled(throttle_on):
    client = APIClient()
    for _ in range(5):
        _post(client)
    r = _post(client)
    assert r.status_code == 429


@pytest.mark.django_db
def test_throttled_response_uses_error_envelope(throttle_on):
    client = APIClient()
    for _ in range(6):
        r = _post(client)
    assert r.status_code == 429
    assert r.data["error"] is True
    assert r.data["status_code"] == 429


@pytest.mark.django_db
def test_valid_login_within_limit_succeeds(throttle_on, admin_user):
    client = APIClient()
    r = client.post(
        LOGIN_URL,
        data={"email": admin_user.email, "password": "testpass123"},
        format="json",
    )
    assert r.status_code == 200
    assert "access" in r.data


@pytest.mark.django_db
def test_refresh_endpoint_not_subject_to_login_throttle(throttle_on, admin_user):
    """Token refresh has no LoginRateThrottle — exhausting login throttle does not affect it."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(admin_user)
    client = APIClient()
    for _ in range(6):
        _post(client)
    r = client.post(REFRESH_URL, data={"refresh": str(refresh)}, format="json")
    assert r.status_code == 200


# ── Throttle INACTIVE ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_throttle_inactive_when_login_rate_not_configured(throttle_off):
    """When 'login' key is absent from DEFAULT_THROTTLE_RATES, no throttle applies."""
    client = APIClient()
    for i in range(10):
        r = _post(client)
        assert r.status_code != 429, f"Should not be throttled at attempt {i + 1}"


# ── Decoupling proof ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_throttle_active_even_when_default_throttle_classes_is_empty(throttle_on):
    """DEFAULT_THROTTLE_CLASSES=[] does NOT disable login throttle.
    Only the absence of the 'login' key in DEFAULT_THROTTLE_RATES does.
    """
    # _THROTTLE_ON has DEFAULT_THROTTLE_CLASSES=[] intentionally.
    client = APIClient()
    for _ in range(5):
        _post(client)
    r = _post(client)
    assert r.status_code == 429
