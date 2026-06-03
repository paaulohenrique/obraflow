from decimal import Decimal

import pytest
from django.utils import timezone

from apps.financeiro.models import CategoriaFinanceira, ContaFinanceira, ContaPagar, LancamentoFinanceiro
from apps.financeiro.services import abrir_caixa, criar_categoria_financeira, criar_conta_financeira


CONTAS_URL = "/api/v1/financeiro/contas-financeiras/"
CATEGORIAS_URL = "/api/v1/financeiro/categorias/"
LANCAMENTOS_URL = "/api/v1/financeiro/lancamentos/"
CONTAS_PAGAR_URL = "/api/v1/financeiro/contas-pagar/"
CAIXAS_URL = "/api/v1/financeiro/caixas/"
DASHBOARD_URL = "/api/v1/financeiro/dashboard/"
CONFIG_URL = "/api/v1/financeiro/configuracao-operacional/"


def detail(base_url, pk):
    return f"{base_url}{pk}/"


@pytest.mark.django_db
class TestFinanceiroViews:
    def test_contas_categorias_lancamentos_e_dashboard(
        self,
        manager_client,
        viewer_client,
        banco,
        receita,
        despesa,
    ):
        create_conta = manager_client.post(
            CONTAS_URL,
            data={"nome": "Banco API", "tipo": ContaFinanceira.TIPO_BANCO},
            format="json",
        )
        assert create_conta.status_code == 201
        conta_id = create_conta.data["id"]

        patch = manager_client.patch(
            detail(CONTAS_URL, conta_id),
            data={"observacao": "Conta atualizada"},
            format="json",
        )
        assert patch.status_code == 200
        assert patch.data["observacao"] == "Conta atualizada"

        ajuste = manager_client.post(
            f"{detail(CONTAS_URL, conta_id)}ajustar-saldo/",
            data={
                "tipo": LancamentoFinanceiro.TIPO_ENTRADA,
                "valor": "200.00",
                "categoria": str(receita.pk),
                "descricao": "Saldo inicial",
            },
            format="json",
        )
        assert ajuste.status_code == 201

        lancamento = manager_client.post(
            LANCAMENTOS_URL,
            data={
                "conta_financeira": conta_id,
                "categoria": str(despesa.pk),
                "tipo": LancamentoFinanceiro.TIPO_SAIDA,
                "valor": "50.00",
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
            },
            format="json",
        )
        assert lancamento.status_code == 201

        dashboard = viewer_client.get(DASHBOARD_URL)
        assert dashboard.status_code == 200
        assert dashboard.data["saldo_total_financeiro"] == "150.00"
        assert dashboard.data["recebido_hoje"] == "200.00"

        list_response = viewer_client.get(LANCAMENTOS_URL + "?ordering=valor")
        assert list_response.status_code == 200
        assert list_response.data["count"] == 2

    def test_conta_pagar_fluxo_api(
        self,
        manager_client,
        banco_com_saldo,
        despesa,
        fornecedor,
    ):
        create = manager_client.post(
            CONTAS_PAGAR_URL,
            data={
                "fornecedor": str(fornecedor.pk),
                "descricao": "Fornecedor API",
                "categoria": str(despesa.pk),
                "valor_total": "80.00",
                "data_vencimento": str(timezone.localdate()),
            },
            format="json",
        )
        assert create.status_code == 201
        conta_id = create.data["id"]

        pagar = manager_client.post(
            f"{detail(CONTAS_PAGAR_URL, conta_id)}pagar/",
            data={
                "conta_financeira": str(banco_com_saldo.pk),
                "valor": "80.00",
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
            },
            format="json",
        )
        assert pagar.status_code == 200
        assert pagar.data["status"] == ContaPagar.STATUS_PAGA
        assert pagar.data["valor_restante"] == "0.00"

    def test_caixa_fluxo_api(self, manager_client, admin_client, caixa, receita):
        abrir = manager_client.post(
            CAIXAS_URL + "abrir/",
            data={"conta_financeira": str(caixa.pk)},
            format="json",
        )
        assert abrir.status_code == 201
        caixa_id = abrir.data["id"]

        lancamento = manager_client.post(
            LANCAMENTOS_URL,
            data={
                "conta_financeira": str(caixa.pk),
                "categoria": str(receita.pk),
                "tipo": LancamentoFinanceiro.TIPO_ENTRADA,
                "valor": "30.00",
                "forma_pagamento": LancamentoFinanceiro.FORMA_DINHEIRO,
            },
            format="json",
        )
        assert lancamento.status_code == 201
        assert str(lancamento.data["caixa_diario"]) == caixa_id

        fechar = manager_client.post(f"{detail(CAIXAS_URL, caixa_id)}fechar/", data={}, format="json")
        assert fechar.status_code == 200
        assert fechar.data["status"] == "FECHADO"
        assert fechar.data["total_entradas"] == "30.00"

        reabrir = admin_client.post(f"{detail(CAIXAS_URL, caixa_id)}reabrir/", data={}, format="json")
        assert reabrir.status_code == 200
        assert reabrir.data["status"] == "ABERTO"

    def test_configuracao_operacional_api(self, manager_client, viewer_client, banco, caixa):
        leitura = viewer_client.get(CONFIG_URL)
        assert leitura.status_code == 200
        assert "destinos_pdv" in leitura.data

        update = manager_client.patch(
            f"{CONFIG_URL}atualizar/",
            data={
                "conta_pix": str(banco.pk),
                "conta_dinheiro": str(caixa.pk),
            },
            format="json",
        )

        assert update.status_code == 200
        assert str(update.data["conta_pix"]) == str(banco.pk)
        assert str(update.data["conta_dinheiro"]) == str(caixa.pk)

        leitura_final = viewer_client.get(CONFIG_URL)
        destinos = {item["forma_pagamento"]: item for item in leitura_final.data["destinos_pdv"]}
        assert str(destinos["PIX"]["conta"]) == str(banco.pk)
        assert str(destinos["DINHEIRO"]["conta"]) == str(caixa.pk)

    def test_permissions_tenant_e_company_payload(
        self,
        manager_client,
        seller_client,
        viewer_client,
        other_company_client,
        anon_client,
        empresa_b,
        manager_user,
    ):
        denied_payload = manager_client.post(
            CONTAS_URL,
            data={"nome": "Com empresa", "tipo": "BANCO", "company": str(empresa_b.pk)},
            format="json",
        )
        assert denied_payload.status_code == 400

        seller_denied = seller_client.post(
            LANCAMENTOS_URL,
            data={},
            format="json",
        )
        assert seller_denied.status_code == 403

        conta = criar_conta_financeira(
            user=manager_user,
            data={"nome": "Banco tenant", "tipo": ContaFinanceira.TIPO_BANCO},
        )
        assert viewer_client.get(detail(CONTAS_URL, conta.pk)).status_code == 200
        assert other_company_client.get(detail(CONTAS_URL, conta.pk)).status_code == 404
        assert anon_client.get(CONTAS_URL).status_code == 401

    def test_cancelar_lancamento_endpoint(self, manager_client, manager_user, banco, receita):
        lancamento = manager_client.post(
            LANCAMENTOS_URL,
            data={
                "conta_financeira": str(banco.pk),
                "categoria": str(receita.pk),
                "tipo": LancamentoFinanceiro.TIPO_ENTRADA,
                "valor": "90.00",
            },
            format="json",
        )
        assert lancamento.status_code == 201
        cancel = manager_client.post(
            f"{detail(LANCAMENTOS_URL, lancamento.data['id'])}cancelar/",
            data={"motivo": "Erro de lançamento"},
            format="json",
        )
        assert cancel.status_code == 200
        assert cancel.data["origem_tipo"] == LancamentoFinanceiro.ORIGEM_ESTORNO

    def test_categoria_criar_e_inativar(self, admin_client, manager_client):
        create = manager_client.post(
            CATEGORIAS_URL,
            data={"nome": "Taxas", "tipo": CategoriaFinanceira.TIPO_DESPESA},
            format="json",
        )
        assert create.status_code == 201
        categoria_id = create.data["id"]

        patch = manager_client.patch(
            detail(CATEGORIAS_URL, categoria_id),
            data={"descricao": "Custos bancários"},
            format="json",
        )
        assert patch.status_code == 200

        inativar_manager = manager_client.post(f"{detail(CATEGORIAS_URL, categoria_id)}inativar/")
        assert inativar_manager.status_code == 403

        inativar_admin = admin_client.post(f"{detail(CATEGORIAS_URL, categoria_id)}inativar/")
        assert inativar_admin.status_code == 200
        assert inativar_admin.data["ativa"] is False

    def test_retrieve_patch_cancelar_e_inativar_endpoints(
        self,
        admin_client,
        manager_client,
        banco,
        despesa,
        fornecedor,
    ):
        conta_resp = manager_client.post(
            CONTAS_URL,
            data={"nome": "Carteira API", "tipo": ContaFinanceira.TIPO_CARTEIRA},
            format="json",
        )
        conta_id = conta_resp.data["id"]
        assert manager_client.get(detail(CONTAS_URL, conta_id)).status_code == 200
        inativar_conta = admin_client.post(f"{detail(CONTAS_URL, conta_id)}inativar/")
        assert inativar_conta.status_code == 200
        assert inativar_conta.data["ativo"] is False

        conta_pagar = manager_client.post(
            CONTAS_PAGAR_URL,
            data={
                "fornecedor": str(fornecedor.pk),
                "descricao": "Despesa editável",
                "categoria": str(despesa.pk),
                "valor_total": "40.00",
                "data_vencimento": str(timezone.localdate()),
            },
            format="json",
        )
        conta_pagar_id = conta_pagar.data["id"]
        retrieve = manager_client.get(detail(CONTAS_PAGAR_URL, conta_pagar_id))
        patch = manager_client.patch(
            detail(CONTAS_PAGAR_URL, conta_pagar_id),
            data={"descricao": "Despesa atualizada", "valor_total": "45.00"},
            format="json",
        )
        cancel = manager_client.post(
            f"{detail(CONTAS_PAGAR_URL, conta_pagar_id)}cancelar/",
            data={"motivo": "Duplicada"},
            format="json",
        )
        assert retrieve.status_code == 200
        assert patch.status_code == 200
        assert patch.data["valor_total"] == "45.00"
        assert cancel.status_code == 200
        assert cancel.data["status"] == ContaPagar.STATUS_CANCELADA

    def test_list_retrieve_caixa_e_filtros(self, manager_client, caixa):
        abrir = manager_client.post(
            CAIXAS_URL + "abrir/",
            data={"conta_financeira": str(caixa.pk)},
            format="json",
        )
        caixa_id = abrir.data["id"]
        retrieve = manager_client.get(detail(CAIXAS_URL, caixa_id))
        list_response = manager_client.get(
            CAIXAS_URL + f"?status=ABERTO&conta_financeira={caixa.pk}&ordering=data"
        )
        assert retrieve.status_code == 200
        assert list_response.status_code == 200
        assert list_response.data["count"] == 1
