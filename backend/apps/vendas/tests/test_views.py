from decimal import Decimal

import pytest

from ..models import Venda
from ..services import criar_venda
from .conftest import make_produto

VENDAS_URL = "/api/v1/pdv/vendas/"


def detail_url(pk):
    return f"{VENDAS_URL}{pk}/"


def _payload(conta, produto, *, quantidade="2.000", preco="30.00"):
    return {
        "itens": [
            {
                "produto": str(produto.pk),
                "forma_venda": None,
                "quantidade_informada": quantidade,
                "preco_unitario": preco,
            }
        ],
        "forma_pagamento": "PIX",
        "conta_financeira": str(conta.pk),
        "desconto": "0.00",
        "observacao": "",
    }


class TestVendaCreate:
    def test_seller_pode_criar(self, seller_client, produto, conta_banco_a):
        response = seller_client.post(VENDAS_URL, _payload(conta_banco_a, produto), format="json")
        assert response.status_code == 201
        assert response.data["status"] == "CONCLUIDA"
        assert response.data["numero"].startswith("PDV-")

    def test_admin_pode_criar(self, admin_client, produto, conta_banco_a):
        response = admin_client.post(VENDAS_URL, _payload(conta_banco_a, produto), format="json")
        assert response.status_code == 201

    def test_viewer_nao_pode_criar(self, viewer_client, produto, conta_banco_a):
        response = viewer_client.post(VENDAS_URL, _payload(conta_banco_a, produto), format="json")
        assert response.status_code == 403

    def test_anon_nao_pode_criar(self, anon_client, produto, conta_banco_a):
        response = anon_client.post(VENDAS_URL, _payload(conta_banco_a, produto), format="json")
        assert response.status_code == 401

    def test_estoque_insuficiente_retorna_400(self, seller_client, produto, conta_banco_a):
        response = seller_client.post(
            VENDAS_URL,
            _payload(conta_banco_a, produto, quantidade="9999.000"),
            format="json",
        )
        assert response.status_code == 400

    def test_itens_vazios_retorna_400(self, seller_client, conta_banco_a):
        payload = {
            "itens": [],
            "forma_pagamento": "PIX",
            "conta_financeira": str(conta_banco_a.pk),
        }
        response = seller_client.post(VENDAS_URL, payload, format="json")
        assert response.status_code == 400

    def test_produto_outra_empresa_retorna_400(self, seller_client, produto_b, conta_banco_a):
        response = seller_client.post(VENDAS_URL, _payload(conta_banco_a, produto_b), format="json")
        assert response.status_code in (400, 404)

    def test_resposta_contem_itens(self, seller_client, produto, conta_banco_a):
        response = seller_client.post(VENDAS_URL, _payload(conta_banco_a, produto), format="json")
        assert response.status_code == 201
        assert len(response.data["itens"]) == 1
        assert response.data["itens"][0]["produto_nome"] == produto.nome


class TestVendaList:
    def test_lista_apenas_da_propria_empresa(self, admin_client, admin_user, produto, conta_banco_a, other_company_client, empresa_b):
        criar_venda(user=admin_user, data={
            "itens": [{"produto": produto.pk, "forma_venda": None, "quantidade_informada": "1.000", "preco_unitario": "30.00"}],
            "forma_pagamento": "PIX",
            "conta_financeira": conta_banco_a,
        })
        response = admin_client.get(VENDAS_URL)
        assert response.status_code == 200
        assert response.data["count"] >= 1

        response_b = other_company_client.get(VENDAS_URL)
        assert response_b.data["count"] == 0

    def test_viewer_pode_listar(self, viewer_client):
        response = viewer_client.get(VENDAS_URL)
        assert response.status_code == 200


class TestVendaRetrieve:
    def test_retrieve_da_propria_empresa(self, admin_client, admin_user, produto, conta_banco_a):
        venda = criar_venda(user=admin_user, data={
            "itens": [{"produto": produto.pk, "forma_venda": None, "quantidade_informada": "1.000", "preco_unitario": "30.00"}],
            "forma_pagamento": "PIX",
            "conta_financeira": conta_banco_a,
        })
        response = admin_client.get(detail_url(venda.pk))
        assert response.status_code == 200
        assert response.data["numero"] == venda.numero

    def test_retrieve_outra_empresa_retorna_404(self, other_company_client, admin_user, produto, conta_banco_a):
        venda = criar_venda(user=admin_user, data={
            "itens": [{"produto": produto.pk, "forma_venda": None, "quantidade_informada": "1.000", "preco_unitario": "30.00"}],
            "forma_pagamento": "PIX",
            "conta_financeira": conta_banco_a,
        })
        response = other_company_client.get(detail_url(venda.pk))
        assert response.status_code == 404


class TestVendaCancelar:
    def _criar(self, user, produto, conta):
        return criar_venda(user=user, data={
            "itens": [{"produto": produto.pk, "forma_venda": None, "quantidade_informada": "1.000", "preco_unitario": "30.00"}],
            "forma_pagamento": "PIX",
            "conta_financeira": conta,
        })

    def test_manager_pode_cancelar(self, manager_user, produto, conta_banco_a):
        from .conftest import auth_client
        venda = self._criar(manager_user, produto, conta_banco_a)
        client = auth_client(manager_user)
        response = client.post(f"{detail_url(venda.pk)}cancelar/", {"motivo": "Devolução"}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "CANCELADA"

    def test_seller_nao_pode_cancelar(self, seller_client, seller_user, produto, conta_banco_a):
        venda = self._criar(seller_user, produto, conta_banco_a)
        response = seller_client.post(f"{detail_url(venda.pk)}cancelar/", {"motivo": "Teste"}, format="json")
        assert response.status_code == 403

    def test_cancelar_sem_motivo_retorna_400(self, admin_client, admin_user, produto, conta_banco_a):
        venda = self._criar(admin_user, produto, conta_banco_a)
        response = admin_client.post(f"{detail_url(venda.pk)}cancelar/", {"motivo": ""}, format="json")
        assert response.status_code == 400


class TestVendaPdf:
    def test_pdf_retorna_binario(self, admin_client, admin_user, produto, conta_banco_a):
        venda = criar_venda(user=admin_user, data={
            "itens": [{"produto": produto.pk, "forma_venda": None, "quantidade_informada": "1.000", "preco_unitario": "30.00"}],
            "forma_pagamento": "PIX",
            "conta_financeira": conta_banco_a,
        })
        response = admin_client.get(f"{detail_url(venda.pk)}pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert len(response.content) > 1000


class TestDashboardVendas:
    def test_dashboard_retorna_dados(self, admin_client):
        response = admin_client.get(f"{VENDAS_URL}dashboard/")
        assert response.status_code == 200
        assert "total_hoje" in response.data
        assert "total_mes" in response.data
        assert "ticket_medio" in response.data
