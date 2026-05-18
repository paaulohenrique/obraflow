import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def empresa_padrao(db):
    from apps.empresas.models import Empresa
    return Empresa.objects.create(
        razao_social="Empresa Teste",
        cnpj="11222333000181",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=10,
    )


@pytest.fixture
def admin_user(db, empresa_padrao):
    from apps.accounts.models import User
    return User.objects.create_superuser(
        email="admin@test.com",
        name="Admin Test",
        password="testpass123",
        company=empresa_padrao,
    )


@pytest.fixture
def auth_client(api_client, admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
