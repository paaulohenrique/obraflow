import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.core.models import AuditLog
from apps.empresas.models import Empresa
from apps.estoque.models import CategoriaProduto, UnidadeMedida
from apps.fiscal.models import ConfiguracaoFiscalEmpresa


FISCAL_URL = "/api/v1/empresas/fiscal/"
CLIENTES_URL = "/api/v1/clientes/"
PRODUTOS_URL = "/api/v1/estoque/produtos/"


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(
        razao_social="Empresa A",
        nome_fantasia="MP Construções",
        cnpj="11222333000181",
    )


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(
        razao_social="Empresa B",
        cnpj="11444777000161",
    )


def make_user(role, empresa, email):
    return User.objects.create_user(
        email=email,
        name=f"User {role}",
        password="testpass123",
        role=role,
        company=empresa,
    )


@pytest.fixture
def manager_user(empresa_a):
    return make_user(User.ROLE_MANAGER, empresa_a, "manager-fiscal@test.com")


@pytest.fixture
def viewer_user(empresa_a):
    return make_user(User.ROLE_VIEWER, empresa_a, "viewer-fiscal@test.com")


@pytest.fixture
def other_manager_user(empresa_b):
    return make_user(User.ROLE_MANAGER, empresa_b, "other-manager-fiscal@test.com")


@pytest.fixture
def manager_client(manager_user):
    return auth_client(manager_user)


@pytest.fixture
def viewer_client(viewer_user):
    return auth_client(viewer_user)


@pytest.fixture
def other_manager_client(other_manager_user):
    return auth_client(other_manager_user)


def fiscal_payload(**kwargs):
    return {
        "cnpj": "11222333000181",
        "razao_social": "MP Construções LTDA",
        "nome_fantasia": "MP Construções",
        "inscricao_estadual": "123456789",
        "inscricao_municipal": "987654",
        "regime_tributario": ConfiguracaoFiscalEmpresa.REGIME_SIMPLES,
        "crt": ConfiguracaoFiscalEmpresa.CRT_SIMPLES,
        "cnae": "4744099",
        "uf": "CE",
        "municipio": "Fortaleza",
        "municipio_ibge": "2304400",
        "logradouro": "Rua Fiscal",
        "numero": "100",
        "bairro": "Centro",
        "cep": "60000000",
        "ambiente_fiscal": ConfiguracaoFiscalEmpresa.AMBIENTE_HOMOLOGACAO,
        "provider_fiscal": ConfiguracaoFiscalEmpresa.PROVIDER_FAKE,
        "provider_company_id": "fake-company",
        "ativo": True,
        **kwargs,
    }


@pytest.mark.django_db
class TestConfiguracaoFiscalEmpresa:
    def test_get_cria_configuracao_com_dados_da_empresa(self, manager_client, empresa_a):
        response = manager_client.get(FISCAL_URL)

        assert response.status_code == 200
        assert response.data["cnpj"] == empresa_a.cnpj
        assert response.data["razao_social"] == empresa_a.razao_social
        assert "provider_token" not in response.data
        assert ConfiguracaoFiscalEmpresa.objects.filter(company=empresa_a).exists()

    def test_manager_atualiza_configuracao_fiscal(self, manager_client):
        response = manager_client.patch(FISCAL_URL, data=fiscal_payload(), format="json")

        assert response.status_code == 200
        assert response.data["cadastro_fiscal_pronto"] is True
        assert response.data["ativo"] is True
        assert AuditLog.objects.filter(entity_type="ConfiguracaoFiscalEmpresa").exists()

    def test_viewer_nao_edita_configuracao_fiscal(self, viewer_client):
        response = viewer_client.patch(FISCAL_URL, data=fiscal_payload(), format="json")

        assert response.status_code == 403

    def test_multi_tenant_configuracao_separada(self, manager_client, other_manager_client):
        assert manager_client.patch(FISCAL_URL, data=fiscal_payload(provider_company_id="a"), format="json").status_code == 200
        assert other_manager_client.patch(
            FISCAL_URL,
            data=fiscal_payload(cnpj="11444777000161", provider_company_id="b"),
            format="json",
        ).status_code == 200

        assert ConfiguracaoFiscalEmpresa.objects.count() == 2
        assert manager_client.get(FISCAL_URL).data["provider_company_id"] == "a"
        assert other_manager_client.get(FISCAL_URL).data["provider_company_id"] == "b"

    def test_dados_sensiveis_sao_rejeitados(self, manager_client):
        response = manager_client.patch(
            FISCAL_URL,
            data={"provider_token": "secret"},
            format="json",
        )

        assert response.status_code == 400
        assert "secret" not in str(response.data)

    def test_validacoes_cnae_ibge_cep(self, manager_client):
        response = manager_client.patch(
            FISCAL_URL,
            data=fiscal_payload(cnae="123", municipio_ibge="230", cep="600"),
            format="json",
        )

        assert response.status_code == 400
        assert "cnae" in str(response.data)
        assert "municipio_ibge" in str(response.data)
        assert "cep" in str(response.data)


def cliente_payload(**kwargs):
    return {
        "nome": "Cliente PJ",
        "tipo_pessoa": Cliente.TIPO_PJ,
        "cpf_cnpj": "11222333000181",
        "cidade": "Fortaleza",
        "estado": "CE",
        "cep": "60000000",
        "rua": "Rua Cliente",
        "numero": "10",
        "bairro": "Centro",
        "municipio_ibge": "2304400",
        "indicador_ie": Cliente.INDICADOR_IE_NAO_CONTRIBUINTE,
        "codigo_pais": "1058",
        "pais": "BRASIL",
        **kwargs,
    }


@pytest.mark.django_db
class TestClienteFiscal:
    def test_ie_obrigatoria_quando_contribuinte(self, manager_client):
        response = manager_client.post(
            CLIENTES_URL,
            data=cliente_payload(indicador_ie=Cliente.INDICADOR_IE_CONTRIBUINTE),
            format="json",
        )

        assert response.status_code == 400
        assert "inscricao_estadual" in str(response.data)

    def test_patch_fiscal_cliente(self, manager_client):
        created = manager_client.post(CLIENTES_URL, data=cliente_payload(), format="json")
        response = manager_client.patch(
            f"{CLIENTES_URL}{created.data['id']}/",
            data={
                "indicador_ie": Cliente.INDICADOR_IE_CONTRIBUINTE,
                "inscricao_estadual": "123456789",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["contribuinte_icms"] is True

    def test_cpf_como_nao_contribuinte(self, manager_client):
        response = manager_client.post(
            CLIENTES_URL,
            data=cliente_payload(
                nome="Cliente PF",
                tipo_pessoa=Cliente.TIPO_PF,
                cpf_cnpj="52998224725",
                indicador_ie=Cliente.INDICADOR_IE_NAO_CONTRIBUINTE,
            ),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["indicador_ie"] == Cliente.INDICADOR_IE_NAO_CONTRIBUINTE


@pytest.fixture
def categoria(empresa_a):
    return CategoriaProduto.objects.create(company=empresa_a, nome="Materiais")


@pytest.fixture
def unidade(empresa_a):
    return UnidadeMedida.objects.create(company=empresa_a, nome="Unidade", sigla="UN")


def produto_payload(categoria, unidade, **kwargs):
    return {
        "nome": "Produto Fiscal",
        "sku": "FISCAL-001",
        "categoria": str(categoria.pk),
        "unidade": str(unidade.pk),
        "preco_compra": "10.00",
        "preco_venda": "15.00",
        "estoque_minimo": "1.000",
        **kwargs,
    }


@pytest.mark.django_db
class TestProdutoFiscal:
    def test_campos_fiscais_opcionais(self, manager_client, categoria, unidade):
        response = manager_client.post(
            PRODUTOS_URL,
            data=produto_payload(categoria, unidade),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["ncm"] == ""
        assert response.data["cadastro_fiscal_pronto"] is False

    def test_produto_fiscal_pronto(self, manager_client, categoria, unidade):
        response = manager_client.post(
            PRODUTOS_URL,
            data=produto_payload(
                categoria,
                unidade,
                ncm="25232910",
                cfop_padrao="5102",
                cst_csosn="102",
                cest="1234567",
                origem_mercadoria="0",
                unidade_tributavel="UN",
            ),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["cadastro_fiscal_pronto"] is True

    def test_validacoes_produto_fiscal(self, manager_client, categoria, unidade):
        response = manager_client.post(
            PRODUTOS_URL,
            data=produto_payload(
                categoria,
                unidade,
                ncm="123",
                cfop_padrao="51",
                cest="123",
                aliquota_icms="-1",
            ),
            format="json",
        )

        assert response.status_code == 400
        assert "ncm" in str(response.data)
        assert "cfop" in str(response.data)
        assert "cest" in str(response.data)
        assert "aliquota_icms" in str(response.data)
