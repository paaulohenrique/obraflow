import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa

# ── Known-valid documents ─────────────────────────────────────────────────────
VALID_CPF_1 = "52998224725"
VALID_CPF_2 = "11144477735"
VALID_CPF_3 = "12345678909"
VALID_CNPJ_1 = "11222333000181"
VALID_CNPJ_2 = "11444777000161"

# Use fixed UUIDs so they are stable across test runs
_COMPANY_A_UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_COMPANY_B_UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


# ── Empresa fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        id=_COMPANY_A_UUID,
        razao_social="Empresa A",
        cnpj="11222333000181",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        id=_COMPANY_B_UUID,
        razao_social="Empresa B",
        cnpj="11444777000161",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


# Keep UUID constants for backward compat in test assertions
COMPANY_A = _COMPANY_A_UUID
COMPANY_B = _COMPANY_B_UUID


# ── User helpers ──────────────────────────────────────────────────────────────

def _make_user(email, role, empresa, **kw):
    return User.objects.create_user(
        email=email,
        name=f"User {role}",
        password="testpass123",
        role=role,
        company=empresa,
        **kw,
    )


def _auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db, empresa_a):
    return _make_user("admin@c.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return _make_user("manager@c.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return _make_user("seller@c.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return _make_user("viewer@c.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def other_company_user(db, empresa_b):
    return _make_user("other@c.com", User.ROLE_ADMIN, empresa_b)


# ── API client fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_client(admin_user):
    return _auth_client(admin_user)


@pytest.fixture
def manager_client(manager_user):
    return _auth_client(manager_user)


@pytest.fixture
def seller_client(seller_user):
    return _auth_client(seller_user)


@pytest.fixture
def viewer_client(viewer_user):
    return _auth_client(viewer_user)


@pytest.fixture
def other_company_client(other_company_user):
    return _auth_client(other_company_user)


@pytest.fixture
def anon_client():
    return APIClient()


# ── Cliente factory + fixtures ────────────────────────────────────────────────

def make_cliente(
    empresa=None,
    cpf_cnpj=VALID_CPF_1,
    nome="João da Silva",
    tipo_pessoa=Cliente.TIPO_PF,
    **kwargs,
):
    if empresa is None:
        empresa = Empresa.objects.get_or_create(
            id=_COMPANY_A_UUID,
            defaults={
                "razao_social": "Empresa A",
                "cnpj": "11222333000181",
                "plano": Empresa.PLANO_BASICO,
                "limite_usuarios": 50,
            },
        )[0]

    defaults = {
        "telefone": "11999990001",
        "whatsapp": "11999990001",
        "email": "joao@test.com",
        "cidade": "São Paulo",
        "estado": "SP",
        "limite_credito": Decimal("1000.00"),
        "saldo_devedor": Decimal("0.00"),
    }
    defaults.update(kwargs)
    return Cliente.objects.create(
        company=empresa,
        nome=nome,
        tipo_pessoa=tipo_pessoa,
        cpf_cnpj=cpf_cnpj,
        **defaults,
    )


@pytest.fixture
def cliente(db, empresa_a):
    return make_cliente(empresa=empresa_a)


@pytest.fixture
def cliente_bloqueado(db, empresa_a):
    return make_cliente(
        empresa=empresa_a,
        cpf_cnpj=VALID_CPF_2,
        nome="Cliente Bloqueado",
        bloqueado=True,
    )


@pytest.fixture
def cliente_inadimplente(db, empresa_a):
    return make_cliente(
        empresa=empresa_a,
        cpf_cnpj=VALID_CPF_3,
        nome="Cliente Inadimplente",
        saldo_devedor=Decimal("500.00"),
    )


@pytest.fixture
def cliente_pj(db, empresa_a):
    return make_cliente(
        empresa=empresa_a,
        cpf_cnpj=VALID_CNPJ_1,
        nome="Empresa LTDA",
        tipo_pessoa=Cliente.TIPO_PJ,
    )


@pytest.fixture
def cliente_outra_empresa(db, empresa_b):
    return make_cliente(
        empresa=empresa_b,
        cpf_cnpj=VALID_CPF_1,
        nome="Cliente Outra Empresa",
    )
