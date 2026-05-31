import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.empresas.models import Empresa
from apps.estoque.models import CategoriaProduto, Fornecedor, Produto, UnidadeMedida

COMPANY_A_UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
COMPANY_B_UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

VALID_CNPJ_A = "11222333000181"
VALID_CNPJ_B = "11444777000161"
VALID_CNPJ_FORNECEDOR_A = "45997418000153"
VALID_CNPJ_FORNECEDOR_B = "11222333000181"


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        id=COMPANY_A_UUID,
        razao_social="Empresa A",
        cnpj=VALID_CNPJ_A,
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        id=COMPANY_B_UUID,
        razao_social="Empresa B",
        cnpj=VALID_CNPJ_B,
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


def make_user(email, role, empresa, **kwargs):
    return User.objects.create_user(
        email=email,
        name=f"User {role}",
        password="testpass123",
        role=role,
        company=empresa,
        **kwargs,
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def admin_user(db, empresa_a):
    return make_user("estoque-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return make_user("estoque-manager@obraflow.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return make_user("estoque-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return make_user("estoque-viewer@obraflow.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def other_company_user(db, empresa_b):
    return make_user("estoque-other@obraflow.com", User.ROLE_ADMIN, empresa_b)


@pytest.fixture
def admin_client(admin_user):
    return auth_client(admin_user)


@pytest.fixture
def manager_client(manager_user):
    return auth_client(manager_user)


@pytest.fixture
def seller_client(seller_user):
    return auth_client(seller_user)


@pytest.fixture
def viewer_client(viewer_user):
    return auth_client(viewer_user)


@pytest.fixture
def other_company_client(other_company_user):
    return auth_client(other_company_user)


@pytest.fixture
def anon_client():
    return APIClient()


def make_unidade(empresa, nome="Unidade", sigla="UN", **kwargs):
    return UnidadeMedida.objects.create(company=empresa, nome=nome, sigla=sigla, **kwargs)


def make_categoria(empresa, nome="Cimento", **kwargs):
    return CategoriaProduto.objects.create(company=empresa, nome=nome, **kwargs)


def make_fornecedor(
    empresa,
    razao_social="Fornecedor Alpha",
    cnpj=VALID_CNPJ_FORNECEDOR_A,
    **kwargs,
):
    return Fornecedor.objects.create(
        company=empresa,
        razao_social=razao_social,
        cnpj=cnpj,
        **kwargs,
    )


def make_produto(
    empresa,
    categoria=None,
    unidade=None,
    fornecedor=None,
    nome="Cimento CP II 50kg",
    sku="CIM-50",
    codigo_barras="789000000001",
    estoque_atual=Decimal("10.000"),
    estoque_minimo=Decimal("2.000"),
    **kwargs,
):
    categoria = categoria or make_categoria(empresa)
    unidade = unidade or make_unidade(empresa)
    fornecedor = fornecedor or make_fornecedor(empresa)
    defaults = {
        "preco_compra": Decimal("25.00"),
        "preco_venda": Decimal("35.00"),
        "custo_medio": Decimal("25.00"),
        "estoque_atual": estoque_atual,
        "estoque_minimo": estoque_minimo,
    }
    defaults.update(kwargs)
    return Produto.objects.create(
        company=empresa,
        nome=nome,
        sku=sku,
        codigo_barras=codigo_barras,
        categoria=categoria,
        unidade=unidade,
        fornecedor_principal=fornecedor,
        **defaults,
    )


@pytest.fixture
def unidade(empresa_a):
    return make_unidade(empresa_a)


@pytest.fixture
def categoria(empresa_a):
    return make_categoria(empresa_a)


@pytest.fixture
def fornecedor(empresa_a):
    return make_fornecedor(empresa_a)


@pytest.fixture
def produto(empresa_a, categoria, unidade, fornecedor):
    return make_produto(
        empresa_a,
        categoria=categoria,
        unidade=unidade,
        fornecedor=fornecedor,
    )


@pytest.fixture
def produto_b(empresa_b):
    return make_produto(
        empresa_b,
        nome="Produto Empresa B",
        sku="B-001",
        codigo_barras="789000000002",
        fornecedor=make_fornecedor(
            empresa_b,
            razao_social="Fornecedor Beta",
            cnpj=VALID_CNPJ_FORNECEDOR_B,
        ),
    )
