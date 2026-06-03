from decimal import Decimal
import uuid

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.fiado.models import ContaFiado
from apps.notificacoes.models import CanalNotificacao


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        razao_social="Empresa A Cobranças",
        nome_fantasia="MP Construções",
        cnpj="55777111000122",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        razao_social="Empresa B Cobranças",
        nome_fantasia="Outra Loja",
        cnpj="66888222000133",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


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
def admin_user(empresa_a):
    return make_user("cobrancas-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def seller_user(empresa_a):
    return make_user("cobrancas-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def other_company_user(empresa_b):
    return make_user("cobrancas-other@obraflow.com", User.ROLE_ADMIN, empresa_b)


@pytest.fixture
def admin_client(admin_user):
    return auth_client(admin_user)


@pytest.fixture
def seller_client(seller_user):
    return auth_client(seller_user)


@pytest.fixture
def other_company_client(other_company_user):
    return auth_client(other_company_user)


@pytest.fixture
def canal_a(empresa_a, admin_user):
    return CanalNotificacao.objects.create(
        company=empresa_a,
        tipo=CanalNotificacao.TIPO_WHATSAPP,
        nome="WhatsApp Principal",
        provider=CanalNotificacao.PROVIDER_META_CLOUD,
        created_by=admin_user,
    )


@pytest.fixture
def canal_b(empresa_b):
    return CanalNotificacao.objects.create(
        company=empresa_b,
        tipo=CanalNotificacao.TIPO_WHATSAPP,
        nome="WhatsApp B",
        provider=CanalNotificacao.PROVIDER_META_CLOUD,
    )


def make_cliente(empresa, *, nome="Cliente Cobrança", telefone="85999990000", whatsapp="85999990000"):
    return Cliente.objects.create(
        company=empresa,
        nome=nome,
        tipo_pessoa=Cliente.TIPO_PF,
        cpf_cnpj=str(uuid.uuid4().int)[:11],
        telefone=telefone,
        whatsapp=whatsapp,
        limite_credito=Decimal("1000.00"),
    )


def make_conta(empresa, cliente, *, vencimento, valor=Decimal("250.00")):
    return ContaFiado.objects.create(
        company=empresa,
        cliente=cliente,
        status=ContaFiado.STATUS_ABERTA,
        valor_total=valor,
        valor_pago=Decimal("0.00"),
        valor_restante=valor,
        data_vencimento=vencimento,
    )
