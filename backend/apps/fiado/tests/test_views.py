from decimal import Decimal

import pytest

from apps.fiado.models import ContaFiado, ItemFiado, PagamentoFiado
from apps.fiado.services import abrir_conta_fiado, adicionar_item_fiado, registrar_pagamento_fiado
from .conftest import make_cliente


CONTAS_URL = "/api/v1/fiado/contas/"
DASHBOARD_URL = "/api/v1/fiado/dashboard/"


def detail(base_url, pk):
    return f"{base_url}{pk}/"


@pytest.mark.django_db
class TestFiadoContaViews:
    def test_seller_abre_conta_e_viewer_apenas_le(self, seller_client, viewer_client, cliente):
        create = seller_client.post(
            CONTAS_URL,
            data={"cliente": str(cliente.pk), "observacao": "Compra da obra"},
            format="json",
        )
        assert create.status_code == 201
        assert str(create.data["cliente"]) == str(cliente.pk)

        list_response = viewer_client.get(CONTAS_URL)
        assert list_response.status_code == 200
        assert list_response.data["count"] == 1

        denied = viewer_client.post(
            CONTAS_URL,
            data={"cliente": str(cliente.pk)},
            format="json",
        )
        assert denied.status_code == 403

    def test_rejeita_company_no_payload(self, seller_client, cliente, empresa_b):
        response = seller_client.post(
            CONTAS_URL,
            data={"cliente": str(cliente.pk), "company": str(empresa_b.pk)},
            format="json",
        )

        assert response.status_code == 400
        assert "company" in str(response.data)

    def test_manager_atualiza_e_admin_cancela_conta(self, admin_client, manager_client, cliente):
        create = manager_client.post(CONTAS_URL, data={"cliente": str(cliente.pk)}, format="json")
        conta_id = create.data["id"]

        patch = manager_client.patch(
            detail(CONTAS_URL, conta_id),
            data={"observacao": "Atualizada"},
            format="json",
        )
        assert patch.status_code == 200
        assert patch.data["observacao"] == "Atualizada"

        cancel_manager = manager_client.post(
            f"{detail(CONTAS_URL, conta_id)}cancelar/",
            data={"motivo": "Sem movimento"},
            format="json",
        )
        assert cancel_manager.status_code == 403

        cancel_admin = admin_client.post(
            f"{detail(CONTAS_URL, conta_id)}cancelar/",
            data={"motivo": "Sem movimento"},
            format="json",
        )
        assert cancel_admin.status_code == 200
        assert cancel_admin.data["status"] == ContaFiado.STATUS_CANCELADA

    def test_tenant_isolation_list_and_retrieve(
        self,
        admin_user,
        admin_client,
        other_company_user,
        other_company_client,
        cliente,
        cliente_b,
    ):
        conta_a = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        conta_b = abrir_conta_fiado(user=other_company_user, data={"cliente": cliente_b})

        list_a = admin_client.get(CONTAS_URL)
        ids_a = [item["id"] for item in list_a.data["results"]]

        assert str(conta_a.pk) in ids_a
        assert str(conta_b.pk) not in ids_a
        assert admin_client.get(detail(CONTAS_URL, conta_b.pk)).status_code == 404
        assert other_company_client.get(detail(CONTAS_URL, conta_a.pk)).status_code == 404

    def test_anonimo_recebe_401(self, anon_client):
        response = anon_client.get(CONTAS_URL)
        assert response.status_code == 401


@pytest.mark.django_db
class TestFiadoItemPagamentoViews:
    def test_seller_adiciona_item_e_registra_pagamento(
        self,
        seller_client,
        seller_user,
        cliente,
        produto,
    ):
        conta = abrir_conta_fiado(user=seller_user, data={"cliente": cliente})

        item_response = seller_client.post(
            f"{detail(CONTAS_URL, conta.pk)}itens/",
            data={"produto": str(produto.pk), "quantidade": "2.000"},
            format="json",
        )
        assert item_response.status_code == 201
        assert item_response.data["subtotal"] == "100.00"

        itens_list = seller_client.get(f"{detail(CONTAS_URL, conta.pk)}itens/")
        assert itens_list.status_code == 200
        assert itens_list.data["count"] == 1

        pagamento_response = seller_client.post(
            f"{detail(CONTAS_URL, conta.pk)}pagamentos/",
            data={"valor": "40.00", "forma_pagamento": PagamentoFiado.FORMA_PIX},
            format="json",
        )
        assert pagamento_response.status_code == 201
        assert pagamento_response.data["valor"] == "40.00"

        pagamentos_list = seller_client.get(f"{detail(CONTAS_URL, conta.pk)}pagamentos/")
        assert pagamentos_list.status_code == 200
        assert pagamentos_list.data["count"] == 1

    def test_manager_cancela_item_e_pagamento(
        self,
        admin_user,
        manager_client,
        cliente,
        produto,
    ):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )
        conta.refresh_from_db()
        pagamento = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("20.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )

        cancel_pagamento = manager_client.post(
            f"/api/v1/fiado/pagamentos/{pagamento.pk}/cancelar/",
            data={"motivo": "Estorno"},
            format="json",
        )
        assert cancel_pagamento.status_code == 200
        assert cancel_pagamento.data["status"] == PagamentoFiado.STATUS_CANCELADO

        cancel_item = manager_client.post(
            f"/api/v1/fiado/itens/{item.pk}/cancelar/",
            data={"motivo": "Cliente desistiu"},
            format="json",
        )
        assert cancel_item.status_code == 200
        assert cancel_item.data["status"] == ItemFiado.STATUS_CANCELADO

    def test_seller_nao_cancela_item(self, admin_user, seller_client, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )

        response = seller_client.post(
            f"/api/v1/fiado/itens/{item.pk}/cancelar/",
            data={"motivo": "Sem permissão"},
            format="json",
        )

        assert response.status_code == 403

    def test_dashboard_endpoint(self, admin_user, admin_client, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )

        response = admin_client.get(DASHBOARD_URL)

        assert response.status_code == 200
        assert response.data["total_em_aberto"] == "50.00"
        assert response.data["contas_abertas"] == 1

    def test_list_filters_search_ordering(self, admin_user, admin_client, empresa_a, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        outro_cliente = make_cliente(empresa_a, nome="Maria Materiais")
        abrir_conta_fiado(user=admin_user, data={"cliente": outro_cliente})

        search = admin_client.get(CONTAS_URL + "?search=Maria")
        ordering = admin_client.get(CONTAS_URL + "?ordering=valor_restante")

        assert search.status_code == 200
        assert search.data["count"] == 1
        assert search.data["results"][0]["cliente_nome"] == "Maria Materiais"
        assert ordering.status_code == 200
