from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.estoque.models import FormaVendaProduto, MovimentacaoEstoque, Produto
from apps.estoque.services import (
    ajuste_estoque,
    ativar_produto,
    cancelar_movimentacao,
    create_produto,
    devolucao_estoque,
    entrada_estoque,
    inativar_produto,
    saida_estoque,
    soft_delete_produto,
    update_produto,
)
from .conftest import make_categoria, make_produto, make_unidade


def produto_payload(categoria, unidade, fornecedor, **kwargs):
    return {
        "nome": "Tijolo 8 furos",
        "descricao": "Milheiro",
        "sku": "tij-8",
        "codigo_barras": "789999900001",
        "categoria": categoria,
        "fornecedor_principal": fornecedor,
        "unidade": unidade,
        "preco_compra": Decimal("0.70"),
        "preco_venda": Decimal("1.10"),
        "custo_medio": Decimal("0.70"),
        "estoque_minimo": Decimal("100.000"),
        **kwargs,
    }


@pytest.mark.django_db
class TestProdutoServices:
    def test_create_produto_sets_company_and_audit(self, admin_user, categoria, unidade, fornecedor):
        produto = create_produto(
            user=admin_user,
            data=produto_payload(categoria, unidade, fornecedor),
        )

        assert produto.company_id == admin_user.company_id
        assert produto.estoque_atual == Decimal("0.000")
        assert produto.sku == "TIJ-8"
        forma = FormaVendaProduto.objects.get(produto=produto, ativo=True)
        assert forma.nome == "Unidade"
        assert forma.fator_conversao == Decimal("1.000000")
        assert forma.preco_venda == Decimal("1.10")
        assert forma.padrao is True
        assert AuditLog.objects.filter(
            entity_type="Produto",
            entity_id=produto.pk,
            action=AuditLog.ACTION_CREATE,
        ).exists()

    def test_update_produto_preserves_estoque_atual(self, admin_user, produto):
        updated = update_produto(
            user=admin_user,
            produto=produto,
            data={"nome": "Cimento atualizado", "estoque_minimo": Decimal("5.000")},
        )

        assert updated.nome == "Cimento atualizado"
        assert updated.estoque_atual == Decimal("10.000")
        assert AuditLog.objects.filter(
            entity_type="Produto",
            entity_id=produto.pk,
            action=AuditLog.ACTION_UPDATE,
        ).exists()

    def test_sku_unique_per_company_active(self, admin_user, produto, categoria, unidade, fornecedor):
        with pytest.raises(ValidationError, match="SKU"):
            create_produto(
                user=admin_user,
                data=produto_payload(
                    categoria,
                    unidade,
                    fornecedor,
                    sku=produto.sku,
                    codigo_barras="789999900002",
                ),
            )

    def test_sku_can_repeat_in_other_company(self, other_company_user, produto):
        categoria = make_categoria(other_company_user.company, nome="Categoria B")
        unidade = make_unidade(other_company_user.company, nome="Unidade B", sigla="UB")
        new = create_produto(
            user=other_company_user,
            data={
                "nome": "Mesmo SKU outra empresa",
                "sku": produto.sku,
                "codigo_barras": "789999900003",
                "categoria": categoria,
                "unidade": unidade,
                "preco_compra": Decimal("1.00"),
                "preco_venda": Decimal("2.00"),
                "custo_medio": Decimal("1.00"),
                "estoque_minimo": Decimal("0.000"),
            },
        )
        assert new.company_id == other_company_user.company_id

    def test_codigo_barras_unique_per_company(self, admin_user, produto, categoria, unidade, fornecedor):
        with pytest.raises(ValidationError, match="Código de barras"):
            create_produto(
                user=admin_user,
                data=produto_payload(
                    categoria,
                    unidade,
                    fornecedor,
                    sku="OUTRO-SKU",
                    codigo_barras=produto.codigo_barras,
                ),
            )

    def test_cross_company_relation_rejected(self, admin_user, produto_b, unidade, fornecedor):
        with pytest.raises(ValidationError, match="empresa"):
            create_produto(
                user=admin_user,
                data=produto_payload(produto_b.categoria, unidade, fornecedor),
            )

    def test_ativar_inativar_and_delete_audit(self, admin_user, produto):
        inativar_produto(user=admin_user, produto=produto)
        produto.refresh_from_db()
        assert produto.is_active is False

        with pytest.raises(ValidationError, match="inativo"):
            inativar_produto(user=admin_user, produto=produto)

        ativar_produto(user=admin_user, produto=produto)
        produto.refresh_from_db()
        assert produto.is_active is True

        with pytest.raises(ValidationError, match="ativo"):
            ativar_produto(user=admin_user, produto=produto)

        soft_delete_produto(user=admin_user, produto=produto)
        produto.refresh_from_db()
        assert produto.is_deleted is True
        assert AuditLog.objects.filter(entity_type="Produto", entity_id=produto.pk).count() == 3

    def test_properties(self, empresa_a, categoria, unidade, fornecedor):
        produto = make_produto(
            empresa_a,
            categoria=categoria,
            unidade=unidade,
            fornecedor=fornecedor,
            preco_compra=Decimal("10.00"),
            preco_venda=Decimal("15.00"),
            estoque_atual=Decimal("1.000"),
            estoque_minimo=Decimal("2.000"),
        )

        assert produto.estoque_baixo is True
        assert produto.margem_percentual == Decimal("50.00")


@pytest.mark.django_db
class TestMovimentacaoServices:
    def test_entrada_aumenta_estoque(self, admin_user, produto, fornecedor):
        mov = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("5.000"),
            custo_unitario=Decimal("20.00"),
            fornecedor=fornecedor,
        )
        produto.refresh_from_db()

        assert mov.tipo == MovimentacaoEstoque.TIPO_ENTRADA
        assert mov.estoque_antes == Decimal("10.000")
        assert mov.estoque_depois == Decimal("15.000")
        assert mov.valor_total == Decimal("100.00")
        assert produto.estoque_atual == Decimal("15.000")

    def test_saida_reduz_estoque(self, admin_user, produto):
        mov = saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("3.000"),
        )
        produto.refresh_from_db()

        assert mov.quantidade_delta == Decimal("-3.000")
        assert produto.estoque_atual == Decimal("7.000")

    def test_saida_sem_saldo_falha(self, admin_user, produto):
        with pytest.raises(ValidationError, match="insuficiente"):
            saida_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("11.000"),
            )

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("10.000")

    def test_ajuste_positivo_e_negativo(self, admin_user, produto):
        ajuste_estoque(
            user=admin_user,
            produto=produto,
            quantidade_delta=Decimal("2.000"),
            motivo="Contagem física",
        )
        ajuste_estoque(
            user=admin_user,
            produto=produto,
            quantidade_delta=Decimal("-1.000"),
            motivo="Perda",
        )
        produto.refresh_from_db()

        assert produto.estoque_atual == Decimal("11.000")

    def test_ajuste_exige_motivo(self, admin_user, produto):
        with pytest.raises(ValidationError, match="Motivo"):
            ajuste_estoque(
                user=admin_user,
                produto=produto,
                quantidade_delta=Decimal("1.000"),
                motivo="",
            )

    def test_devolucao_aumenta_estoque(self, admin_user, produto):
        mov = devolucao_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("2.000"),
            motivo="Cliente devolveu",
        )
        produto.refresh_from_db()

        assert mov.tipo == MovimentacaoEstoque.TIPO_DEVOLUCAO
        assert produto.estoque_atual == Decimal("12.000")

    def test_cancelamento_cria_reverso_e_marca_original(self, admin_user, produto):
        saida = saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("4.000"),
        )
        cancelamento = cancelar_movimentacao(
            user=admin_user,
            movimentacao=saida,
            motivo="Venda cancelada",
        )
        produto.refresh_from_db()
        saida.refresh_from_db()

        assert cancelamento.tipo == MovimentacaoEstoque.TIPO_CANCELAMENTO
        assert cancelamento.quantidade_delta == Decimal("4.000")
        assert cancelamento.movimentacao_cancelada_id == saida.pk
        assert saida.status == MovimentacaoEstoque.STATUS_CANCELADA
        assert produto.estoque_atual == Decimal("10.000")

    def test_duplo_cancelamento_falha(self, admin_user, produto):
        saida = saida_estoque(user=admin_user, produto=produto, quantidade=Decimal("1.000"))
        cancelar_movimentacao(user=admin_user, movimentacao=saida, motivo="Cancelado")

        with pytest.raises(ValidationError, match="cancelada"):
            cancelar_movimentacao(user=admin_user, movimentacao=saida, motivo="Outra vez")

    def test_idempotency_key_nao_duplica_estoque(self, admin_user, produto):
        first = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("5.000"),
            idempotency_key="compra-123",
        )
        second = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("5.000"),
            idempotency_key="compra-123",
        )
        produto.refresh_from_db()

        assert second.pk == first.pk
        assert produto.estoque_atual == Decimal("15.000")

    def test_movimentacao_imutavel_e_nao_deletavel(self, admin_user, produto):
        mov = entrada_estoque(user=admin_user, produto=produto, quantidade=Decimal("1.000"))
        mov.motivo = "tentativa"

        with pytest.raises(RuntimeError, match="imutável"):
            mov.save()
        with pytest.raises(RuntimeError, match="imutável"):
            mov.delete()
        with pytest.raises(RuntimeError, match="imutável"):
            MovimentacaoEstoque.objects.filter(pk=mov.pk).delete()

    def test_rejects_zero_and_inactive_product(self, admin_user, produto):
        with pytest.raises(ValidationError, match="maior que zero"):
            entrada_estoque(user=admin_user, produto=produto, quantidade=Decimal("0.000"))
        with pytest.raises(ValidationError, match="maior que zero"):
            saida_estoque(user=admin_user, produto=produto, quantidade=Decimal("0.000"))
        with pytest.raises(ValidationError, match="não pode ser zero"):
            ajuste_estoque(
                user=admin_user,
                produto=produto,
                quantidade_delta=Decimal("0.000"),
                motivo="Zero",
            )
        with pytest.raises(ValidationError, match="maior que zero"):
            devolucao_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("0.000"),
                motivo="Zero",
            )

        produto.is_active = False
        produto.save(update_fields=["is_active", "updated_at"])
        with pytest.raises(ValidationError, match="inativo"):
            entrada_estoque(user=admin_user, produto=produto, quantidade=Decimal("1.000"))

    def test_cross_company_fornecedor_rejected(self, admin_user, produto, produto_b):
        with pytest.raises(ValidationError, match="empresa"):
            entrada_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("1.000"),
                fornecedor=produto_b.fornecedor_principal,
            )

    def test_cancelamento_validation_edges(self, admin_user, produto):
        entrada = entrada_estoque(user=admin_user, produto=produto, quantidade=Decimal("1.000"))

        with pytest.raises(ValidationError, match="Motivo"):
            cancelar_movimentacao(user=admin_user, movimentacao=entrada, motivo="")

        cancelamento = cancelar_movimentacao(
            user=admin_user,
            movimentacao=entrada,
            motivo="Compra cancelada",
            idempotency_key="cancel-1",
        )
        same = cancelar_movimentacao(
            user=admin_user,
            movimentacao=entrada,
            motivo="Compra cancelada",
            idempotency_key="cancel-1",
        )
        assert same.pk == cancelamento.pk

        with pytest.raises(ValidationError, match="cancelamento"):
            cancelar_movimentacao(
                user=admin_user,
                movimentacao=cancelamento,
                motivo="Não pode",
            )
