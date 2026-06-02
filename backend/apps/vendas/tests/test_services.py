from decimal import Decimal

import pytest

from apps.estoque.models import MovimentacaoEstoque
from apps.financeiro.models import LancamentoFinanceiro

from ..models import ItemVenda, Venda
from ..services import cancelar_venda, criar_venda
from .conftest import make_forma_venda, make_produto


def _venda_payload(conta, produto, *, forma_venda=None, quantidade="2.000", preco="30.00", desconto="0.00"):
    return {
        "itens": [
            {
                "produto": produto.pk,
                "forma_venda": forma_venda,
                "quantidade_informada": quantidade,
                "preco_unitario": preco,
            }
        ],
        "forma_pagamento": Venda.FORMA_PIX,
        "conta_financeira": conta,
        "desconto": desconto,
        "observacao": "",
    }


class TestCriarVenda:
    def test_cria_venda_simples(self, admin_user, produto, conta_banco_a):
        venda = criar_venda(
            user=admin_user,
            data=_venda_payload(conta_banco_a, produto),
        )
        assert venda.pk is not None
        assert venda.status == Venda.STATUS_CONCLUIDA
        assert venda.numero.startswith("PDV-")
        assert venda.valor_subtotal == Decimal("60.00")   # 2 × 30.00
        assert venda.valor_total == Decimal("60.00")
        assert venda.desconto == Decimal("0.00")
        assert venda.forma_pagamento == Venda.FORMA_PIX
        assert venda.lancamento_financeiro is not None

    def test_subtotal_e_total_com_desconto(self, admin_user, produto, conta_banco_a):
        venda = criar_venda(
            user=admin_user,
            data=_venda_payload(conta_banco_a, produto, desconto="10.00"),
        )
        assert venda.valor_subtotal == Decimal("60.00")
        assert venda.valor_total == Decimal("50.00")

    def test_cria_item_venda(self, admin_user, produto, conta_banco_a):
        venda = criar_venda(
            user=admin_user,
            data=_venda_payload(conta_banco_a, produto),
        )
        assert ItemVenda.objects.filter(venda=venda).count() == 1
        item = ItemVenda.objects.get(venda=venda)
        assert item.quantidade == Decimal("2.000")
        assert item.quantidade_informada == Decimal("2.000")
        assert item.subtotal == Decimal("60.00")

    def test_baixa_estoque(self, admin_user, produto, conta_banco_a):
        estoque_antes = produto.estoque_atual
        criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        produto.refresh_from_db()
        assert produto.estoque_atual == estoque_antes - Decimal("2.000")

    def test_movimentacao_saida_criada(self, admin_user, produto, conta_banco_a):
        criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        mov = MovimentacaoEstoque.objects.filter(
            produto=produto, tipo=MovimentacaoEstoque.TIPO_SAIDA
        ).first()
        assert mov is not None
        assert mov.quantidade_delta == Decimal("-2.000")

    def test_lancamento_financeiro_criado(self, admin_user, produto, conta_banco_a):
        venda = criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        lan = venda.lancamento_financeiro
        assert lan is not None
        assert lan.tipo == LancamentoFinanceiro.TIPO_ENTRADA
        assert lan.valor == Decimal("60.00")
        assert lan.forma_pagamento == Venda.FORMA_PIX
        assert lan.status == LancamentoFinanceiro.STATUS_CONFIRMADO

    def test_venda_com_forma_venda(self, admin_user, produto, forma_venda, conta_banco_a):
        """1 saco = 50kg. Produto tem 50kg em estoque → 1 saco consome tudo."""
        venda = criar_venda(
            user=admin_user,
            data=_venda_payload(conta_banco_a, produto, forma_venda=forma_venda, quantidade="1.000", preco="80.00"),
        )
        item = ItemVenda.objects.get(venda=venda)
        assert item.quantidade_informada == Decimal("1.000")
        assert item.quantidade == Decimal("50.000")   # 1 × 50kg
        assert item.subtotal == Decimal("80.00")      # 1 × 80.00

    def test_estoque_insuficiente_levanta_erro(self, admin_user, produto, conta_banco_a):
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Estoque insuficiente"):
            criar_venda(
                user=admin_user,
                data=_venda_payload(conta_banco_a, produto, quantidade="9999.000"),
            )

    def test_lista_vazia_levanta_erro(self, admin_user, conta_banco_a):
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError):
            criar_venda(
                user=admin_user,
                data={
                    "itens": [],
                    "forma_pagamento": Venda.FORMA_PIX,
                    "conta_financeira": conta_banco_a,
                },
            )

    def test_desconto_maior_que_subtotal_levanta_erro(self, admin_user, produto, conta_banco_a):
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Desconto"):
            criar_venda(
                user=admin_user,
                data=_venda_payload(conta_banco_a, produto, desconto="999.00"),
            )

    def test_tenant_isolation(self, admin_user, produto_b, conta_banco_a):
        from rest_framework.exceptions import ValidationError
        with pytest.raises((ValidationError, Exception)):
            criar_venda(
                user=admin_user,
                data=_venda_payload(conta_banco_a, produto_b),
            )

    def test_multiplos_itens(self, admin_user, empresa_a, conta_banco_a):
        p1 = make_produto(empresa_a, nome="Produto X", estoque_atual=Decimal("20.000"), preco_venda=Decimal("10.00"))
        p2 = make_produto(empresa_a, nome="Produto Y", estoque_atual=Decimal("20.000"), preco_venda=Decimal("20.00"))
        venda = criar_venda(
            user=admin_user,
            data={
                "itens": [
                    {"produto": p1.pk, "forma_venda": None, "quantidade_informada": "3.000", "preco_unitario": "10.00"},
                    {"produto": p2.pk, "forma_venda": None, "quantidade_informada": "2.000", "preco_unitario": "20.00"},
                ],
                "forma_pagamento": Venda.FORMA_DINHEIRO,
                "conta_financeira": ContaFinanceira.objects.get(company=empresa_a, tipo=ContaFinanceira.TIPO_CAIXA),
            },
        )
        assert ItemVenda.objects.filter(venda=venda).count() == 2
        assert venda.valor_subtotal == Decimal("70.00")   # 30 + 40

    def test_venda_dinheiro_requer_caixa(self, admin_user, produto, empresa_a):
        """Forma DINHEIRO com conta tipo BANCO deve falhar."""
        from rest_framework.exceptions import ValidationError
        conta_banco = ContaFinanceira.objects.get(company=empresa_a, tipo=ContaFinanceira.TIPO_BANCO)
        payload = {
            "itens": [
                {
                    "produto": produto.pk,
                    "forma_venda": None,
                    "quantidade_informada": "2.000",
                    "preco_unitario": "30.00",
                }
            ],
            "forma_pagamento": Venda.FORMA_DINHEIRO,  # DINHEIRO exige conta CAIXA
            "conta_financeira": conta_banco,           # conta BANCO → deve falhar
            "desconto": "0.00",
        }
        with pytest.raises(ValidationError):
            criar_venda(user=admin_user, data=payload)


class TestCancelarVenda:
    def test_cancela_venda(self, admin_user, produto, conta_banco_a):
        venda = criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        resultado = cancelar_venda(user=admin_user, venda=venda, motivo="Cancelamento teste")
        assert resultado.status == Venda.STATUS_CANCELADA
        assert resultado.motivo_cancelamento == "Cancelamento teste"
        assert resultado.cancelled_by == admin_user

    def test_cancela_reverte_estoque(self, admin_user, produto, conta_banco_a):
        estoque_original = produto.estoque_atual
        venda = criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        produto.refresh_from_db()
        assert produto.estoque_atual < estoque_original
        cancelar_venda(user=admin_user, venda=venda, motivo="Cancelamento teste")
        produto.refresh_from_db()
        assert produto.estoque_atual == estoque_original

    def test_cancela_reverte_lancamento(self, admin_user, produto, conta_banco_a):
        venda = criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        lancamento = venda.lancamento_financeiro
        cancelar_venda(user=admin_user, venda=venda, motivo="Cancelamento teste")
        lancamento.refresh_from_db()
        assert lancamento.status == LancamentoFinanceiro.STATUS_CANCELADO

    def test_cancelar_ja_cancelada_levanta_erro(self, admin_user, produto, conta_banco_a):
        from rest_framework.exceptions import ValidationError
        venda = criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        cancelar_venda(user=admin_user, venda=venda, motivo="Primeira vez")
        with pytest.raises(ValidationError, match="já foi cancelada"):
            cancelar_venda(user=admin_user, venda=venda, motivo="Segunda vez")

    def test_cancelar_sem_motivo_levanta_erro(self, admin_user, produto, conta_banco_a):
        from rest_framework.exceptions import ValidationError
        venda = criar_venda(user=admin_user, data=_venda_payload(conta_banco_a, produto))
        with pytest.raises(ValidationError, match="Motivo"):
            cancelar_venda(user=admin_user, venda=venda, motivo="")


# importação tardia para evitar erro de circular import
from apps.financeiro.models import ContaFinanceira  # noqa: E402
