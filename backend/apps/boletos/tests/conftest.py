import uuid
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.boletos.models import BoletoOCR
from apps.empresas.models import Empresa
from apps.estoque.models import Fornecedor
from apps.financeiro.models import CategoriaFinanceira


COMPANY_A_UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
COMPANY_B_UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.BOLETOS_OCR_PROVIDER = "FAKE"
    settings.BOLETOS_FAKE_OCR_TEXT = ""


@pytest.fixture(autouse=True)
def disable_enqueue(monkeypatch):
    monkeypatch.setattr("apps.boletos.services.boleto._enqueue_ocr", lambda boleto: None)


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
    return make_user("boletos-admin@obraflow.com", User.ROLE_ADMIN, empresa_a)


@pytest.fixture
def manager_user(db, empresa_a):
    return make_user("boletos-manager@obraflow.com", User.ROLE_MANAGER, empresa_a)


@pytest.fixture
def seller_user(db, empresa_a):
    return make_user("boletos-seller@obraflow.com", User.ROLE_SELLER, empresa_a)


@pytest.fixture
def viewer_user(db, empresa_a):
    return make_user("boletos-viewer@obraflow.com", User.ROLE_VIEWER, empresa_a)


@pytest.fixture
def other_company_user(db, empresa_b):
    return make_user("boletos-other@obraflow.com", User.ROLE_ADMIN, empresa_b)


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


def pdf_file(name="boleto.pdf", body=b""):
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n" + body + b"\n%%EOF"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def jpg_file(name="boleto.jpg", body=b"imagem"):
    return SimpleUploadedFile(name, b"\xff\xd8\xff\xe0" + body, content_type="image/jpeg")


def fake_line():
    from apps.boletos.services.extracao import _mod10_digit

    field1 = "001912345"
    field2 = "6789012345"
    field3 = "6789012345"
    tail = "1000" + "0000012345"
    return (
        field1
        + str(_mod10_digit(field1))
        + field2
        + str(_mod10_digit(field2))
        + field3
        + str(_mod10_digit(field3))
        + "1"
        + tail
    )


def make_categoria_financeira(empresa, *, nome="Fornecedor", tipo=CategoriaFinanceira.TIPO_DESPESA):
    return CategoriaFinanceira.objects.create(company=empresa, nome=nome, tipo=tipo)


@pytest.fixture
def despesa(empresa_a):
    return make_categoria_financeira(empresa_a)


@pytest.fixture
def receita(empresa_a):
    return make_categoria_financeira(empresa_a, nome="Receita", tipo=CategoriaFinanceira.TIPO_RECEITA)


@pytest.fixture
def fornecedor(empresa_a):
    return Fornecedor.objects.create(
        company=empresa_a,
        razao_social="Energisa Teste",
        nome_fantasia="Energisa",
        cnpj="45997418000153",
    )


def make_boleto(empresa, user, **kwargs):
    defaults = {
        "arquivo": pdf_file(f"boleto-{uuid.uuid4().hex}.pdf"),
        "arquivo_nome_original": "boleto.pdf",
        "tipo_arquivo": BoletoOCR.TIPO_PDF,
        "content_type": "application/pdf",
        "tamanho_bytes": 128,
        "sha256": uuid.uuid4().hex + uuid.uuid4().hex,
        "status": BoletoOCR.STATUS_AGUARDANDO_REVISAO,
        "fornecedor_nome": "Energisa Teste",
        "documento_beneficiario": "45997418000153",
        "banco_codigo": "001",
        "banco_nome": "Banco do Brasil",
        "valor": Decimal("123.45"),
        "vencimento": "2026-06-30",
        "linha_digitavel": "",
        "codigo_barras": "",
        "created_by": user,
    }
    defaults.update(kwargs)
    return BoletoOCR.objects.create(company=empresa, **defaults)
