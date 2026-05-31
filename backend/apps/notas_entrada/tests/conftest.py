"""Fixtures compartilhadas para testes do módulo notas_entrada."""
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.empresas.models import Empresa
from apps.estoque.models import CategoriaProduto, Fornecedor, Produto, UnidadeMedida
from apps.financeiro.models import CategoriaFinanceira

FIXTURES_DIR = Path(__file__).parent / "fixtures"

COMPANY_A_UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
COMPANY_B_UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

# CNPJ do emitente no XML de fixture
CNPJ_FORNECEDOR_XML = "12345678000195"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


# ── Empresas ─────────────────────────────────────────────────────────────────


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        id=COMPANY_A_UUID,
        razao_social="Empresa A Ltda",
        cnpj="11222333000181",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        id=COMPANY_B_UUID,
        razao_social="Empresa B SA",
        cnpj="11444777000161",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


# ── Usuários ──────────────────────────────────────────────────────────────────


def make_user(email, role, empresa):
    return User.objects.create_user(
        email=email,
        name=f"User {role}",
        password="testpass123",
        role=role,
        company=empresa,
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def admin_user(db, empresa_a):
    return make_user("nota-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return make_user("nota-manager@obraflow.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return make_user("nota-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return make_user("nota-viewer@obraflow.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def user_b(db, empresa_b):
    return make_user("nota-b@obraflow.com", User.ROLE_ADMIN, empresa_b)


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
def anon_client():
    return APIClient()


@pytest.fixture
def client_b(user_b):
    return auth_client(user_b)


# ── Estoque ───────────────────────────────────────────────────────────────────


@pytest.fixture
def fornecedor_a(db, empresa_a):
    return Fornecedor.objects.create(
        company=empresa_a,
        razao_social="Distribuidora Teste Ltda",
        cnpj=CNPJ_FORNECEDOR_XML,
        telefone="",
        email="",
    )


@pytest.fixture
def unidade(db, empresa_a):
    return UnidadeMedida.objects.create(company=empresa_a, nome="Saco", sigla="SC")


@pytest.fixture
def unidade_un(db, empresa_a):
    return UnidadeMedida.objects.create(company=empresa_a, nome="Unidade", sigla="UN")


@pytest.fixture
def categoria_produto(db, empresa_a):
    return CategoriaProduto.objects.create(company=empresa_a, nome="Construção")


@pytest.fixture
def produto_cimento(db, empresa_a, categoria_produto, unidade):
    return Produto.objects.create(
        company=empresa_a,
        nome="Cimento CP-II 50kg",
        sku="",
        codigo_barras="7891000315507",
        categoria=categoria_produto,
        unidade=unidade,
        preco_compra=Decimal("25.00"),
        preco_venda=Decimal("32.00"),
    )


@pytest.fixture
def produto_sem_ean(db, empresa_a, categoria_produto, unidade_un):
    return Produto.objects.create(
        company=empresa_a,
        nome="Produto Sem EAN",
        sku="AREIA-F-001",
        codigo_barras="",
        categoria=categoria_produto,
        unidade=unidade_un,
        preco_compra=Decimal("10.00"),
        preco_venda=Decimal("15.00"),
    )


# ── Financeiro ────────────────────────────────────────────────────────────────


@pytest.fixture
def categoria_despesa(db, empresa_a):
    return CategoriaFinanceira.objects.create(
        company=empresa_a,
        nome="Compras de Material",
        tipo=CategoriaFinanceira.TIPO_DESPESA,
    )


# ── Arquivos XML ──────────────────────────────────────────────────────────────


def xml_file(filename="nfe_valida.xml", name="nfe_valida.xml") -> SimpleUploadedFile:
    path = FIXTURES_DIR / filename
    content = path.read_bytes()
    return SimpleUploadedFile(name, content, content_type="text/xml")


def xml_bytes(filename="nfe_valida.xml") -> bytes:
    return (FIXTURES_DIR / filename).read_bytes()
