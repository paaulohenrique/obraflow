import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.empresas.models import Empresa

VALID_CNPJ_A = "11222333000181"
VALID_CNPJ_B = "11444777000161"
VALID_CNPJ_C = "45997418000153"  # another valid CNPJ for create tests


def _make_empresa(cnpj=VALID_CNPJ_A, razao_social="Empresa Alpha", **kwargs):
    defaults = {"plano": Empresa.PLANO_BASICO, "limite_usuarios": 10}
    defaults.update(kwargs)
    return Empresa.objects.create(cnpj=cnpj, razao_social=razao_social, **defaults)


def _make_user(email, role, empresa, **kw):
    return User.objects.create_superuser(
        email=email,
        name=f"User {role}",
        password="testpass123",
        role=role,
        is_staff=True,
        company=empresa,
        **kw,
    )


def _auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def empresa_alpha(db):
    return _make_empresa(cnpj=VALID_CNPJ_A, razao_social="Empresa Alpha")


@pytest.fixture
def empresa_beta(db):
    return _make_empresa(cnpj=VALID_CNPJ_B, razao_social="Empresa Beta")


@pytest.fixture
def superuser(db, empresa_alpha):
    return _make_user("super@obraflow.com", User.ROLE_ADMIN, empresa_alpha, is_superuser=True)


@pytest.fixture
def regular_admin(db, empresa_alpha):
    return User.objects.create_user(
        email="admin@alpha.com",
        name="Admin Alpha",
        password="testpass123",
        role=User.ROLE_ADMIN,
        company=empresa_alpha,
        is_staff=False,
    )


@pytest.fixture
def super_client(superuser):
    return _auth_client(superuser)


@pytest.fixture
def regular_client(regular_admin):
    return _auth_client(regular_admin)


@pytest.fixture
def anon_client():
    return APIClient()
