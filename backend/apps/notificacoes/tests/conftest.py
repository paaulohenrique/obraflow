import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.notificacoes.models import CanalNotificacao, TemplateNotificacao

COMPANY_A_UUID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
COMPANY_B_UUID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        id=COMPANY_A_UUID,
        razao_social="Empresa A Notif",
        cnpj="11333555000122",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        id=COMPANY_B_UUID,
        razao_social="Empresa B Notif",
        cnpj="22444666000133",
        plano=Empresa.PLANO_BASICO,
        limite_usuarios=50,
    )


def _make_user(email, role, empresa):
    return User.objects.create_user(
        email=email,
        name=f"User {role}",
        password="testpass123",
        role=role,
        company=empresa,
    )


def _auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def admin_user(db, empresa_a):
    return _make_user("notif-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return _make_user("notif-manager@obraflow.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return _make_user("notif-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return _make_user("notif-viewer@obraflow.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def other_company_user(db, empresa_b):
    return _make_user("notif-other@obraflow.com", User.ROLE_ADMIN, empresa_b)


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


@pytest.fixture
def canal_a(db, empresa_a, admin_user):
    return CanalNotificacao.objects.create(
        company=empresa_a,
        tipo=CanalNotificacao.TIPO_WHATSAPP,
        nome="WhatsApp Principal",
        provider=CanalNotificacao.PROVIDER_META_CLOUD,
        created_by=admin_user,
    )


@pytest.fixture
def canal_b(db, empresa_b):
    return CanalNotificacao.objects.create(
        company=empresa_b,
        tipo=CanalNotificacao.TIPO_WHATSAPP,
        nome="WhatsApp B",
        provider=CanalNotificacao.PROVIDER_META_CLOUD,
    )


@pytest.fixture
def template_cobranca(db, empresa_a, canal_a):
    return TemplateNotificacao.objects.create(
        company=empresa_a,
        canal=canal_a,
        nome="Cobrança Fiado",
        tipo=TemplateNotificacao.TIPO_COBRANCA_FIADO,
        provider_template_name="cobranca_fiado_v1",
        linguagem="pt_BR",
        categoria=TemplateNotificacao.CATEGORIA_UTILITY,
    )


@pytest.fixture
def template_confirmacao(db, empresa_a, canal_a):
    return TemplateNotificacao.objects.create(
        company=empresa_a,
        canal=canal_a,
        nome="Confirmação Pagamento",
        tipo=TemplateNotificacao.TIPO_CONFIRMACAO_PAGAMENTO,
        provider_template_name="confirmacao_pagamento_v1",
        linguagem="pt_BR",
        categoria=TemplateNotificacao.CATEGORIA_UTILITY,
    )


@pytest.fixture
def cliente_a(db, empresa_a):
    return Cliente.objects.create(
        company=empresa_a,
        nome="Cliente Teste",
        telefone="83999999999",
        cpf_cnpj="12345678901",
        tipo_pessoa=Cliente.TIPO_PF,
        limite_credito=Decimal("1000.00"),
    )


@pytest.fixture
def conta_fiado_a(db, empresa_a, cliente_a, admin_user):
    from apps.fiado.services.conta import abrir_conta_fiado
    return abrir_conta_fiado(
        user=admin_user,
        data={"cliente": cliente_a},
    )


@pytest.fixture
def pagamento_fiado_a(db, empresa_a, conta_fiado_a, admin_user):
    from apps.fiado.models import PagamentoFiado

    # Cria o pagamento direto via ORM para evitar cadeia de validações do service
    return PagamentoFiado.objects.create(
        company=empresa_a,
        conta=conta_fiado_a,
        valor=Decimal("50.00"),
        forma_pagamento=PagamentoFiado.FORMA_PIX,
        status=PagamentoFiado.STATUS_CONFIRMADO,
        created_by=admin_user,
    )
