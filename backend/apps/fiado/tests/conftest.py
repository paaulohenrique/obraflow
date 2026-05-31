import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.estoque.models import CategoriaProduto, Fornecedor, Produto, UnidadeMedida


COMPANY_A_UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
COMPANY_B_UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        id=COMPANY_A_UUID,
        razao_social="Empresa A",
        cnpj="11222333000181",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        id=COMPANY_B_UUID,
        razao_social="Empresa B",
        cnpj="11444777000161",
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
    return make_user("fiado-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return make_user("fiado-manager@obraflow.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return make_user("fiado-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return make_user("fiado-viewer@obraflow.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def other_company_user(db, empresa_b):
    return make_user("fiado-other@obraflow.com", User.ROLE_ADMIN, empresa_b)


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


def make_cliente(
    empresa,
    *,
    nome="Cliente Fiado",
    cpf_cnpj=None,
    limite_credito=Decimal("1000.00"),
    saldo_devedor=Decimal("0.00"),
    bloqueado=False,
    is_active=True,
):
    cpf_cnpj = cpf_cnpj or str(uuid.uuid4().int)[:11]
    return Cliente.objects.create(
        company=empresa,
        nome=nome,
        tipo_pessoa=Cliente.TIPO_PF,
        cpf_cnpj=cpf_cnpj,
        telefone="85999990000",
        whatsapp="85999990000",
        limite_credito=limite_credito,
        saldo_devedor=saldo_devedor,
        bloqueado=bloqueado,
        is_active=is_active,
    )


def make_produto(
    empresa,
    *,
    nome="Cimento CP II",
    sku=None,
    codigo_barras=None,
    estoque_atual=Decimal("10.000"),
    preco_venda=Decimal("50.00"),
    is_active=True,
):
    suffix = uuid.uuid4().hex[:8].upper()
    unidade = UnidadeMedida.objects.create(company=empresa, nome=f"Unidade {suffix}", sigla=suffix[:6])
    categoria = CategoriaProduto.objects.create(company=empresa, nome=f"Categoria {suffix}")
    fornecedor = Fornecedor.objects.create(
        company=empresa,
        razao_social=f"Fornecedor {suffix}",
        cnpj=str(uuid.uuid4().int)[:14],
    )
    return Produto.objects.create(
        company=empresa,
        nome=nome,
        sku=sku or f"SKU-{suffix}",
        codigo_barras=codigo_barras or f"BAR-{suffix}",
        categoria=categoria,
        fornecedor_principal=fornecedor,
        unidade=unidade,
        preco_compra=Decimal("30.00"),
        preco_venda=preco_venda,
        custo_medio=Decimal("30.00"),
        estoque_atual=estoque_atual,
        estoque_minimo=Decimal("1.000"),
        is_active=is_active,
    )


@pytest.fixture
def cliente(empresa_a):
    return make_cliente(empresa_a)


@pytest.fixture
def cliente_bloqueado(empresa_a):
    return make_cliente(
        empresa_a,
        nome="Cliente Bloqueado",
        bloqueado=True,
    )


@pytest.fixture
def cliente_inativo(empresa_a):
    return make_cliente(
        empresa_a,
        nome="Cliente Inativo",
        is_active=False,
    )


@pytest.fixture
def cliente_b(empresa_b):
    return make_cliente(empresa_b, nome="Cliente Empresa B")


@pytest.fixture
def produto(empresa_a):
    return make_produto(empresa_a)


@pytest.fixture
def produto_b(empresa_b):
    return make_produto(empresa_b, nome="Produto Empresa B")
