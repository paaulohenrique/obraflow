import django
import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def reset_db_sequences(db):
    """Fixture available to all tests that need the database."""
    pass


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User
    return User.objects.create_superuser(
        email="admin@test.com",
        name="Admin Test",
        password="testpass123",
    )


@pytest.fixture
def auth_client(api_client, admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
