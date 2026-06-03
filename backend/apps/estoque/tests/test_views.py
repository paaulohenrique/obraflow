from decimal import Decimal

import pytest

from apps.core.models import AuditLog
from apps.estoque.models import FormaVendaProduto, MovimentacaoEstoque, Produto
from apps.estoque.services import entrada_estoque
from .conftest import make_categoria, make_fornecedor, make_produto, make_unidade

UNIDADES_URL = "/api/v1/estoque/unidades/"
CATEGORIAS_URL = "/api/v1/estoque/categorias/"
FORNECEDORES_URL = "/api/v1/estoque/fornecedores/"
PRODUTOS_URL = "/api/v1/estoque/produtos/"
MOVIMENTACOES_URL = "/api/v1/estoque/movimentacoes/"


def detail(base_url, pk):
    return f"{base_url}{pk}/"


def produto_payload(categoria, unidade, fornecedor, **kwargs):
    return {
        "nome": "Areia média",
        "descricao": "Metro cúbico",
        "sku": "AREIA-MEDIA",
        "codigo_barras": "789123450001",
        "categoria": str(categoria.pk),
        "fornecedor_principal": str(fornecedor.pk),
        "unidade": str(unidade.pk),
        "preco_compra": "100.00",
        "preco_venda": "140.00",
        "custo_medio": "100.00",
        "estoque_minimo": "5.000",
        **kwargs,
    }


@pytest.mark.django_db
class TestCatalogoViews:
    def test_admin_creates_unidade_categoria_fornecedor(self, admin_client):
        r_unidade = admin_client.post(
            UNIDADES_URL,
            data={"nome": "Saco", "sigla": "sc", "descricao": "Saco"},
            format="json",
        )
        r_categoria = admin_client.post(
            CATEGORIAS_URL,
            data={"nome": "Argamassas", "descricao": "Linha seca"},
            format="json",
        )
        r_fornecedor = admin_client.post(
            FORNECEDORES_URL,
            data={"razao_social": "Fornecedor Teste", "cnpj": "45.997.418/0001-53"},
            format="json",
        )

        assert r_unidade.status_code == 201
        assert r_unidade.data["sigla"] == "SC"
        assert r_categoria.status_code == 201
        assert r_fornecedor.status_code == 201
        assert r_fornecedor.data["cnpj"] == "45997418000153"

    def test_viewer_can_list_but_not_create(self, viewer_client):
        assert viewer_client.get(CATEGORIAS_URL).status_code == 200
        r = viewer_client.post(CATEGORIAS_URL, data={"nome": "X"}, format="json")
        assert r.status_code == 403

    def test_admin_can_soft_delete_catalog_item(self, admin_client, categoria):
        r = admin_client.delete(detail(CATEGORIAS_URL, categoria.pk))
        assert r.status_code == 204

        r_list = admin_client.get(CATEGORIAS_URL)
        ids = [item["id"] for item in r_list.data["results"]]
        assert str(categoria.pk) not in ids

    def test_retrieve_and_update_catalog_items(self, manager_client, unidade, fornecedor):
        r_detail = manager_client.get(detail(UNIDADES_URL, unidade.pk))
        r_update = manager_client.put(
            detail(UNIDADES_URL, unidade.pk),
            data={"nome": "Unidade put", "sigla": "UP", "descricao": "Atualizada"},
            format="json",
        )
        r_fornecedor = manager_client.patch(
            detail(FORNECEDORES_URL, fornecedor.pk),
            data={"nome_fantasia": "Fantasia nova"},
            format="json",
        )

        assert r_detail.status_code == 200
        assert r_update.status_code == 200
        assert r_update.data["nome"] == "Unidade put"
        assert r_fornecedor.status_code == 200
        assert r_fornecedor.data["nome_fantasia"] == "Fantasia nova"


@pytest.mark.django_db
class TestProdutoViews:
    def test_manager_can_create_product(self, manager_client, categoria, unidade, fornecedor):
        r = manager_client.post(
            PRODUTOS_URL,
            data=produto_payload(categoria, unidade, fornecedor),
            format="json",
        )

        assert r.status_code == 201
        assert r.data["estoque_atual"] == "0.000"
        assert Produto.objects.filter(pk=r.data["id"]).exists()
        assert FormaVendaProduto.objects.filter(produto_id=r.data["id"], ativo=True).exists()

    def test_garantir_forma_venda_action(self, manager_client, produto):
        r = manager_client.post(f"{detail(PRODUTOS_URL, produto.pk)}garantir-forma-venda/")

        assert r.status_code == 200
        assert r.data["nome"] == "Unidade"
        assert r.data["fator_conversao"] == "1.000000"

        repetir = manager_client.post(f"{detail(PRODUTOS_URL, produto.pk)}garantir-forma-venda/")
        assert repetir.status_code == 200
        assert repetir.data["id"] == r.data["id"]

    def test_auditoria_operacional_lista_produtos_sem_forma(self, viewer_client, produto):
        r = viewer_client.get(f"{PRODUTOS_URL}auditoria-operacional/")

        assert r.status_code == 200
        ids = [item["id"] for item in r.data["sem_forma_venda"]["results"]]
        assert str(produto.pk) in ids

    def test_seller_and_viewer_cannot_create_product(self, seller_client, viewer_client):
        assert seller_client.post(PRODUTOS_URL, data={}, format="json").status_code == 403
        assert viewer_client.post(PRODUTOS_URL, data={}, format="json").status_code == 403

    def test_update_inativar_ativar_delete(self, admin_client, manager_client, produto):
        put_payload = produto_payload(produto.categoria, produto.unidade, produto.fornecedor_principal)
        put_payload["nome"] = "Cimento via put"
        r_put = manager_client.put(detail(PRODUTOS_URL, produto.pk), data=put_payload, format="json")
        assert r_put.status_code == 200
        assert r_put.data["nome"] == "Cimento via put"

        r_update = manager_client.patch(
            detail(PRODUTOS_URL, produto.pk),
            data={"nome": "Cimento novo"},
            format="json",
        )
        assert r_update.status_code == 200
        assert r_update.data["nome"] == "Cimento novo"

        r_inativar = manager_client.post(f"{detail(PRODUTOS_URL, produto.pk)}inativar/")
        assert r_inativar.status_code == 200
        assert r_inativar.data["is_active"] is False

        r_ativar = manager_client.post(f"{detail(PRODUTOS_URL, produto.pk)}ativar/")
        assert r_ativar.status_code == 200
        assert r_ativar.data["is_active"] is True

        r_delete = admin_client.delete(detail(PRODUTOS_URL, produto.pk))
        assert r_delete.status_code == 204

    def test_manager_cannot_delete_product(self, manager_client, produto):
        r = manager_client.delete(detail(PRODUTOS_URL, produto.pk))
        assert r.status_code == 403

    def test_list_filters_search_ordering_and_low_stock(self, admin_client, empresa_a, produto):
        make_produto(
            empresa_a,
            categoria=make_categoria(empresa_a, nome="Baixo estoque"),
            unidade=make_unidade(empresa_a, nome="Metro", sigla="M3"),
            fornecedor=make_fornecedor(
                empresa_a,
                razao_social="Fornecedor Baixo",
                cnpj="11222333000181",
            ),
            nome="Produto baixo",
            sku="BAIXO",
            codigo_barras="789123450099",
            estoque_atual=Decimal("1.000"),
            estoque_minimo=Decimal("2.000"),
        )

        r_search = admin_client.get(PRODUTOS_URL + "?search=cimento")
        assert r_search.status_code == 200
        assert r_search.data["count"] == 1

        r_low = admin_client.get(PRODUTOS_URL + "baixo-estoque/")
        assert r_low.status_code == 200
        assert r_low.data["count"] == 1
        assert r_low.data["results"][0]["sku"] == "BAIXO"

        r_order = admin_client.get(PRODUTOS_URL + "?ordering=-estoque_atual")
        estoques = [Decimal(p["estoque_atual"]) for p in r_order.data["results"]]
        assert estoques == sorted(estoques, reverse=True)

    def test_tenant_isolation_on_list_and_retrieve(self, admin_client, other_company_client, produto, produto_b):
        r = admin_client.get(PRODUTOS_URL)
        ids = [item["id"] for item in r.data["results"]]

        assert str(produto.pk) in ids
        assert str(produto_b.pk) not in ids
        assert other_company_client.get(detail(PRODUTOS_URL, produto.pk)).status_code == 404

    def test_cross_company_relation_rejected_by_serializer(
        self,
        admin_client,
        categoria,
        unidade,
        fornecedor,
        produto_b,
    ):
        payload = produto_payload(categoria, unidade, fornecedor)
        payload["categoria"] = str(produto_b.categoria_id)
        r = admin_client.post(PRODUTOS_URL, data=payload, format="json")
        assert r.status_code == 400
        assert "categoria" in str(r.data)

    def test_company_payload_is_rejected(self, admin_client, categoria, unidade, fornecedor, empresa_b):
        payload = produto_payload(categoria, unidade, fornecedor)
        payload["company"] = str(empresa_b.pk)

        r = admin_client.post(PRODUTOS_URL, data=payload, format="json")

        assert r.status_code == 400
        assert "company" in str(r.data)


@pytest.mark.django_db
class TestMovimentacaoViews:
    def test_admin_manager_and_seller_permissions(self, admin_client, manager_client, seller_client, viewer_client, produto):
        entrada = admin_client.post(
            MOVIMENTACOES_URL + "entrada/",
            data={"produto": str(produto.pk), "quantidade": "2.000"},
            format="json",
        )
        assert entrada.status_code == 201

        ajuste = manager_client.post(
            MOVIMENTACOES_URL + "ajuste/",
            data={"produto": str(produto.pk), "quantidade": "1.000", "motivo": "Contagem"},
            format="json",
        )
        assert ajuste.status_code == 201

        saida = seller_client.post(
            MOVIMENTACOES_URL + "saida/",
            data={"produto": str(produto.pk), "quantidade": "1.000"},
            format="json",
        )
        assert saida.status_code == 201

        viewer_saida = viewer_client.post(
            MOVIMENTACOES_URL + "saida/",
            data={"produto": str(produto.pk), "quantidade": "1.000"},
            format="json",
        )
        assert viewer_saida.status_code == 403

    def test_viewer_can_list_and_retrieve(self, admin_user, viewer_client, produto):
        mov = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("1.000"),
        )

        r_list = viewer_client.get(MOVIMENTACOES_URL)
        r_detail = viewer_client.get(detail(MOVIMENTACOES_URL, mov.pk))

        assert r_list.status_code == 200
        assert r_list.data["count"] == 1
        assert r_detail.status_code == 200
        assert r_detail.data["id"] == str(mov.pk)

    def test_saida_insuficiente_returns_400(self, admin_client, produto):
        r = admin_client.post(
            MOVIMENTACOES_URL + "saida/",
            data={"produto": str(produto.pk), "quantidade": "999.000"},
            format="json",
        )
        assert r.status_code == 400
        assert "insuficiente" in str(r.data).lower()

    def test_cancelar_endpoint_and_double_cancel(self, admin_client, produto):
        saida = admin_client.post(
            MOVIMENTACOES_URL + "saida/",
            data={"produto": str(produto.pk), "quantidade": "2.000"},
            format="json",
        )
        mov_id = saida.data["id"]

        cancel = admin_client.post(
            f"{detail(MOVIMENTACOES_URL, mov_id)}cancelar/",
            data={"motivo": "Venda cancelada"},
            format="json",
        )
        double = admin_client.post(
            f"{detail(MOVIMENTACOES_URL, mov_id)}cancelar/",
            data={"motivo": "Outra vez"},
            format="json",
        )

        assert cancel.status_code == 201
        assert cancel.data["tipo"] == MovimentacaoEstoque.TIPO_CANCELAMENTO
        assert double.status_code == 400

    def test_movimentacoes_do_produto_action(self, admin_user, admin_client, produto):
        entrada_estoque(user=admin_user, produto=produto, quantidade=Decimal("1.000"))

        r = admin_client.get(f"{detail(PRODUTOS_URL, produto.pk)}movimentacoes/")

        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_cross_company_cannot_move_product(self, admin_client, produto_b):
        r = admin_client.post(
            MOVIMENTACOES_URL + "entrada/",
            data={"produto": str(produto_b.pk), "quantidade": "1.000"},
            format="json",
        )
        assert r.status_code == 400

    def test_audit_log_for_movements(self, admin_client, produto):
        r = admin_client.post(
            MOVIMENTACOES_URL + "entrada/",
            data={"produto": str(produto.pk), "quantidade": "2.000"},
            format="json",
        )

        assert r.status_code == 201
        assert AuditLog.objects.filter(
            entity_type="MovimentacaoEstoque",
            action=AuditLog.ACTION_CREATE,
        ).exists()
