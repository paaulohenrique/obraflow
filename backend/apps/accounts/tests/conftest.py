import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.empresas.models import Empresa


# ── Known-valid CNPJ fixtures ─────────────────────────────────────────────────

CNPJ_ALPHA = "11222333000181"
CNPJ_BETA = "11444777000161"


# ── Empresa fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def empresa_alpha(db):
    return Empresa.objects.create(
        razao_social="Alpha Materiais",
        cnpj=CNPJ_ALPHA,
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=20,
    )


@pytest.fixture
def empresa_beta(db):
    return Empresa.objects.create(
        razao_social="Beta Construções",
        cnpj=CNPJ_BETA,
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=20,
    )


# ── User factory ──────────────────────────────────────────────────────────────

def make_user(email, role, empresa, password="testpass123", **kw):
    return User.objects.create_user(
        email=email,
        name=f"User {role}",
        password=password,
        role=role,
        company=empresa,
        **kw,
    )


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def admin_alpha(db, empresa_alpha):
    return make_user("admin@alpha.com", User.ROLE_ADMIN, empresa_alpha)


@pytest.fixture
def manager_alpha(db, empresa_alpha):
    return make_user("manager@alpha.com", User.ROLE_MANAGER, empresa_alpha)


@pytest.fixture
def seller_alpha(db, empresa_alpha):
    return make_user("seller@alpha.com", User.ROLE_SELLER, empresa_alpha)


@pytest.fixture
def viewer_alpha(db, empresa_alpha):
    return make_user("viewer@alpha.com", User.ROLE_VIEWER, empresa_alpha)


@pytest.fixture
def admin_beta(db, empresa_beta):
    return make_user("admin@beta.com", User.ROLE_ADMIN, empresa_beta)


@pytest.fixture
def superuser(db, empresa_alpha):
    return User.objects.create_superuser(
        email="super@obraflow.com",
        name="Platform Admin",
        password="testpass123",
        company=empresa_alpha,
    )


# ── API client helpers ────────────────────────────────────────────────────────

def auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def admin_alpha_client(admin_alpha):
    return auth_client_for(admin_alpha)


@pytest.fixture
def manager_alpha_client(manager_alpha):
    return auth_client_for(manager_alpha)


@pytest.fixture
def super_client(superuser):
    return auth_client_for(superuser)
