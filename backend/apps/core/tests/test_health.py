"""Tests for the HealthCheckView."""
import pytest
from unittest.mock import patch
from django.urls import reverse


HEALTH_URL = "/api/health/"


@pytest.mark.django_db
def test_health_check_returns_ok_when_all_services_up(client):
    response = client.get(HEALTH_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.django_db
def test_health_check_envelope_has_required_keys(client):
    response = client.get(HEALTH_URL)
    for key in ("status", "database", "redis"):
        assert key in response.json()


@pytest.mark.django_db
def test_health_check_no_auth_required(client):
    """Health endpoint must be publicly accessible."""
    response = client.get(HEALTH_URL)
    assert response.status_code != 401
    assert response.status_code != 403


@pytest.mark.django_db
def test_health_check_503_when_database_fails(client):
    with patch("apps.core.views._check_database", return_value="error"):
        response = client.get(HEALTH_URL)
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["database"] == "error"


@pytest.mark.django_db
def test_health_check_503_when_redis_fails(client):
    with patch("apps.core.views._check_redis", return_value="error"):
        response = client.get(HEALTH_URL)
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["redis"] == "error"


@pytest.mark.django_db
def test_health_check_200_when_only_database_ok_redis_ok(client):
    """Sanity: both OK → 200."""
    with (
        patch("apps.core.views._check_database", return_value="ok"),
        patch("apps.core.views._check_redis", return_value="ok"),
    ):
        response = client.get(HEALTH_URL)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
