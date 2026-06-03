import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.estoque.models import CategoriaProduto, FormaVendaProduto, Fornecedor, Produto, UnidadeMedida
from apps.financeiro.models import CaixaDiario, CategoriaFinanceira, ContaFinanceira


COMPANY_A_UUID = uuid.UUID("aa000000-0000-0000-0000-000000000001")
COMPANY_B_UUID = uuid.UUID("bb000000-0000-0000-0000-000000000002")


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        id=COMPANY_A_UUID,
        razao_social="Empresa Vendas A",
        cnpj="11333555000170",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        id=COMPANY_B_UUID,
        razao_social="Empresa Vendas B",
        cnpj="22444666000145",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


def _setup_financeiro(empresa):
    banco = ContaFinanceira.objects.create(
        company=empresa, nome="Banco PDV", tipo=ContaFinanceira.TIPO_BANCO
    )
    caixa_cf = ContaFinanceira.objects.create(
        company=empresa, nome="Caixa PDV", tipo=ContaFinanceira.TIPO_CAIXA
    )
    caixa_diario = CaixaDiario.objects.create(
        company=empresa,
        conta_financeira=caixa_cf,
        saldo_inicial=Decimal("0.00"),
        saldo_final=Decimal("0.00"),
    )
    categoria = CategoriaFinanceira.objects.create(
        company=empresa, nome="Receita Vendas", tipo=CategoriaFinanceira.TIPO_RECEITA
    )
    return banco, caixa_cf, caixa_diario, categoria


@pytest.fixture(autouse=True)
def financeiro_padrao(db, empresa_a, empresa_b):
    _setup_financeiro(empresa_a)
    _setup_financeiro(empresa_b)


@pytest.fixture
def conta_banco_a(db, empresa_a, financeiro_padrao):
    return ContaFinanceira.objects.get(company=empresa_a, tipo=ContaFinanceira.TIPO_BANCO)


@pytest.fixture
def conta_caixa_a(db, empresa_a, financeiro_padrao):
    return ContaFinanceira.objects.get(company=empresa_a, tipo=ContaFinanceira.TIPO_CAIXA)


def make_user(email, role, empresa):
    return User.objects.create_user(
        email=email, name=f"User {role}", password="testpass123",
        role=role, company=empresa,
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def admin_user(db, empresa_a):
    return make_user("pdv-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return make_user("pdv-manager@obraflow.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return make_user("pdv-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return make_user("pdv-viewer@obraflow.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def other_company_user(db, empresa_b):
    return make_user("pdv-other@obraflow.com", User.ROLE_ADMIN, empresa_b)


@pytest.fixture
def admin_client(admin_user):
    return auth_client(admin_user)


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


def make_produto(empresa, *, nome="Cimento", estoque_atual=Decimal("50.000"), preco_venda=Decimal("30.00")):
    suffix = uuid.uuid4().hex[:8].upper()
    unidade = UnidadeMedida.objects.create(company=empresa, nome=f"Un {suffix}", sigla=suffix[:5])
    categoria = CategoriaProduto.objects.create(company=empresa, nome=f"Cat {suffix}")
    fornecedor = Fornecedor.objects.create(
        company=empresa, razao_social=f"Forn {suffix}", cnpj=str(uuid.uuid4().int)[:14]
    )
    return Produto.objects.create(
        company=empresa, nome=nome, sku=f"SKU-{suffix}",
        codigo_barras=f"BAR-{suffix}", categoria=categoria,
        fornecedor_principal=fornecedor, unidade=unidade,
        preco_compra=Decimal("20.00"), preco_venda=preco_venda,
        custo_medio=Decimal("20.00"), estoque_atual=estoque_atual,
        estoque_minimo=Decimal("1.000"),
    )


def make_forma_venda(empresa, produto, *, nome="Saco", unidade="saco", fator=Decimal("50.000"), preco=Decimal("80.00")):
    return FormaVendaProduto.objects.create(
        company=empresa, produto=produto, nome=nome, codigo=f"FV-{uuid.uuid4().hex[:6]}",
        unidade=unidade, fator_conversao=fator, preco_venda=preco, padrao=True,
    )


def make_cliente(empresa, *, nome="Cliente PDV"):
    cpf = str(uuid.uuid4().int)[:11]
    return Cliente.objects.create(
        company=empresa, nome=nome, tipo_pessoa=Cliente.TIPO_PF,
        cpf_cnpj=cpf, telefone="85999990000",
    )


@pytest.fixture
def produto(db, empresa_a):
    return make_produto(empresa_a)


@pytest.fixture
def produto_b(db, empresa_b):
    return make_produto(empresa_b, nome="Produto B")


@pytest.fixture
def forma_venda(db, empresa_a, produto):
    return make_forma_venda(empresa_a, produto)


@pytest.fixture
def cliente(db, empresa_a):
    return make_cliente(empresa_a)
