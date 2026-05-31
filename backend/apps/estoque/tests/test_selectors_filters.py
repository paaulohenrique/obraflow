from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.estoque.filters import ProdutoFilter
from apps.estoque.models import MovimentacaoEstoque
from apps.estoque.selectors import (
    get_categoria_by_id,
    get_fornecedor_by_id,
    get_movimentacao_by_id,
    get_produto_by_id,
    get_unidade_by_id,
    produtos_baixo_estoque,
    search_movimentacoes,
    search_produtos,
)
from apps.estoque.services import entrada_estoque
from .conftest import make_categoria, make_fornecedor, make_produto, make_unidade


@pytest.mark.django_db
def test_get_by_id_selectors_and_not_found(admin_user, produto, categoria, unidade, fornecedor):
    mov = entrada_estoque(user=admin_user, produto=produto, quantidade=Decimal("1.000"))

    assert get_produto_by_id(company_id=admin_user.company_id, produto_id=produto.pk) == produto
    assert get_categoria_by_id(company_id=admin_user.company_id, categoria_id=categoria.pk) == categoria
    assert get_unidade_by_id(company_id=admin_user.company_id, unidade_id=unidade.pk) == unidade
    assert get_fornecedor_by_id(company_id=admin_user.company_id, fornecedor_id=fornecedor.pk) == fornecedor
    assert get_movimentacao_by_id(company_id=admin_user.company_id, movimentacao_id=mov.pk) == mov

    with pytest.raises(NotFound):
        get_produto_by_id(company_id=admin_user.company_id, produto_id="00000000-0000-0000-0000-000000000000")
    with pytest.raises(PermissionDenied):
        search_produtos(company_id=None)


@pytest.mark.django_db
def test_search_produtos_filters_all_supported_fields(admin_user, empresa_a, produto):
    baixo = make_produto(
        empresa_a,
        categoria=make_categoria(empresa_a, nome="Busca Categoria"),
        unidade=make_unidade(empresa_a, nome="Busca Unidade", sigla="BU"),
        fornecedor=make_fornecedor(
            empresa_a,
            razao_social="Fornecedor Busca",
            cnpj="11222333000181",
        ),
        nome="Baixo Estoque Busca",
        sku="BUSCA",
        codigo_barras="789555000001",
        estoque_atual=Decimal("1.000"),
        estoque_minimo=Decimal("5.000"),
        preco_venda=Decimal("50.00"),
    )
    produto.is_active = False
    produto.save(update_fields=["is_active", "updated_at"])

    filters = {
        "search": "busca",
        "categoria": str(baixo.categoria_id),
        "fornecedor": str(baixo.fornecedor_principal_id),
        "unidade": str(baixo.unidade_id),
        "is_active": "true",
        "estoque_baixo": "true",
        "preco_venda__gte": "40.00",
        "preco_venda__lte": "60.00",
    }
    qs = search_produtos(company_id=admin_user.company_id, filters=filters)

    assert list(qs) == [baixo]
    assert list(produtos_baixo_estoque(company_id=admin_user.company_id)) == [baixo]
    assert search_produtos(
        company_id=admin_user.company_id,
        filters={"estoque_baixo": "false"},
    ).count() == 1
    assert search_produtos(
        company_id=admin_user.company_id,
        filters={"preco_venda__gte": "invalid", "preco_venda__lte": "invalid"},
    ).count() == 2


@pytest.mark.django_db
def test_search_movimentacoes_filters(admin_user, produto, fornecedor):
    mov = entrada_estoque(
        user=admin_user,
        produto=produto,
        quantidade=Decimal("2.000"),
        fornecedor=fornecedor,
        idempotency_key="selector-key",
    )
    now = timezone.now().isoformat()

    qs = search_movimentacoes(
        company_id=admin_user.company_id,
        filters={
            "produto": str(produto.pk),
            "tipo": MovimentacaoEstoque.TIPO_ENTRADA,
            "status": MovimentacaoEstoque.STATUS_ATIVA,
            "fornecedor": str(fornecedor.pk),
            "created_by": str(admin_user.pk),
            "created_at_before": now,
        },
    )

    assert list(qs) == [mov]
    assert search_movimentacoes(
        company_id=admin_user.company_id,
        filters={"created_at_after": now},
    ).count() == 0


@pytest.mark.django_db
def test_produto_filter_methods(admin_user, produto):
    base = search_produtos(company_id=admin_user.company_id)
    product_filter = ProdutoFilter()

    assert product_filter.filter_search(base, "search", "").count() == 1
    assert product_filter.filter_search(base, "search", produto.sku).count() == 1
    assert product_filter.filter_estoque_baixo(base, "estoque_baixo", None).count() == 1
    assert product_filter.filter_estoque_baixo(base, "estoque_baixo", False).count() == 1
