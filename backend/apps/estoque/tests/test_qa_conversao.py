"""QA Manual → Automatizado: cenários reais de Fio, Cimento, Bloco + auditoria de conversão."""
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.estoque.models import FormaVendaProduto, MovimentacaoEstoque
from apps.estoque.services import entrada_estoque, saida_estoque
from apps.estoque.tests.conftest import (
    make_categoria,
    make_fornecedor,
    make_produto,
    make_unidade,
    VALID_CNPJ_FORNECEDOR_A,
    VALID_CNPJ_FORNECEDOR_B,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def forma(empresa, produto, nome, codigo, unidade_sigla, fator, preco=Decimal("0.00"),
           padrao=False, ativo=True, permite_fracionado=True):
    return FormaVendaProduto.objects.create(
        company=empresa,
        produto=produto,
        nome=nome,
        codigo=codigo,
        unidade=unidade_sigla,
        fator_conversao=fator,
        preco_venda=preco,
        ativo=ativo,
        padrao=padrao,
        permite_fracionado=permite_fracionado,
    )


def set_estoque(produto, qtd: Decimal):
    produto.estoque_atual = qtd
    produto.save(update_fields=["estoque_atual"])
    produto.refresh_from_db()


# ──────────────────────────────────────────────
# QA FIO
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestQAFio:
    """
    Produto: Fio 2.5mm
    Unidade base: Metro
    Formas de venda: Metro (×1), Rolo 100m (×100)
    """

    def _setup(self, empresa, user, categoria, unidade_metro):
        prod = make_produto(
            empresa,
            categoria=categoria,
            unidade=unidade_metro,
            nome="Fio 2.5mm",
            sku="FIO-25",
            codigo_barras="001",
            estoque_atual=Decimal("0.000"),
        )
        f_metro = forma(empresa, prod, "Metro", "M", "M", Decimal("1"), padrao=True)
        f_rolo = forma(empresa, prod, "Rolo 100m", "ROLO", "ROLO", Decimal("100"))
        return prod, f_metro, f_rolo

    def test_entrada_3_rolos_resulta_300_metros(self, admin_user, empresa_a, categoria, unidade):
        prod, f_metro, f_rolo = self._setup(empresa_a, admin_user, categoria, unidade)

        mov = entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("300.000"),
            forma_venda=f_rolo, quantidade_informada=Decimal("3.000"),
        )
        prod.refresh_from_db()

        assert prod.estoque_atual == Decimal("300.000")
        assert mov.quantidade_delta == Decimal("300.000")
        assert mov.quantidade_informada == Decimal("3.000")
        assert mov.forma_venda_id == f_rolo.pk

    def test_venda_20_metros_reduz_corretamente(self, admin_user, empresa_a, categoria, unidade):
        prod, f_metro, f_rolo = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("300.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("20.000"),
            forma_venda=f_metro, quantidade_informada=Decimal("20.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("280.000")

    def test_venda_2_rolos_reduz_200_metros(self, admin_user, empresa_a, categoria, unidade):
        prod, f_metro, f_rolo = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("280.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("200.000"),
            forma_venda=f_rolo, quantidade_informada=Decimal("2.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("80.000")

    def test_venda_1_rolo_com_estoque_insuficiente(self, admin_user, empresa_a, categoria, unidade):
        prod, f_metro, f_rolo = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("80.000"))

        with pytest.raises(ValidationError, match="[Ee]stoque"):
            saida_estoque(
                user=admin_user, produto=prod,
                quantidade=Decimal("100.000"),  # 1 rolo = 100m > 80m disponíveis
                forma_venda=f_rolo, quantidade_informada=Decimal("1.000"),
            )

    def test_fluxo_completo_fio(self, admin_user, empresa_a, categoria, unidade):
        """Fluxo encadeado: entrada 3 rolos → venda 20m → venda 2 rolos → erro 1 rolo."""
        prod, f_metro, f_rolo = self._setup(empresa_a, admin_user, categoria, unidade)

        # Entrada: 3 rolos = 300m
        entrada_estoque(user=admin_user, produto=prod, quantidade=Decimal("300"),
                        forma_venda=f_rolo, quantidade_informada=Decimal("3"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("300.000")

        # Venda: 20m
        saida_estoque(user=admin_user, produto=prod, quantidade=Decimal("20"),
                      forma_venda=f_metro, quantidade_informada=Decimal("20"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("280.000")

        # Venda: 2 rolos = 200m
        saida_estoque(user=admin_user, produto=prod, quantidade=Decimal("200"),
                      forma_venda=f_rolo, quantidade_informada=Decimal("2"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("80.000")

        # Venda: 1 rolo = 100m → insuficiente
        with pytest.raises(ValidationError, match="[Ee]stoque"):
            saida_estoque(user=admin_user, produto=prod, quantidade=Decimal("100"),
                          forma_venda=f_rolo, quantidade_informada=Decimal("1"))


# ──────────────────────────────────────────────
# QA CIMENTO
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestQACimento:
    """
    Produto: Cimento CP-II
    Unidade base: Kg
    Formas de venda: Kg (×1), Saco 50kg (×50)
    """

    def _setup(self, empresa, user, categoria, unidade_kg):
        prod = make_produto(
            empresa, categoria=categoria, unidade=unidade_kg,
            nome="Cimento CP-II", sku="CIM-001", codigo_barras="002",
            estoque_atual=Decimal("0.000"),
        )
        f_kg = forma(empresa, prod, "Kg", "KG", "KG", Decimal("1"), padrao=True)
        f_saco = forma(empresa, prod, "Saco 50kg", "SACO", "SACO", Decimal("50"))
        return prod, f_kg, f_saco

    def test_entrada_10_sacos_resulta_500_kg(self, admin_user, empresa_a, categoria, unidade):
        prod, f_kg, f_saco = self._setup(empresa_a, admin_user, categoria, unidade)

        entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("500.000"),
            forma_venda=f_saco, quantidade_informada=Decimal("10.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("500.000")

    def test_venda_25kg(self, admin_user, empresa_a, categoria, unidade):
        prod, f_kg, f_saco = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("500.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("25.000"),
            forma_venda=f_kg, quantidade_informada=Decimal("25.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("475.000")

    def test_venda_1_saco(self, admin_user, empresa_a, categoria, unidade):
        prod, f_kg, f_saco = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("475.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("50.000"),
            forma_venda=f_saco, quantidade_informada=Decimal("1.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("425.000")

    def test_venda_1_saco_com_500kg_resulta_450kg(self, admin_user, empresa_a, categoria, unidade):
        prod, f_kg, f_saco = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("500.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("1.000"),
            forma_venda=f_saco, quantidade_informada=Decimal("1.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("450.000")

    def test_fluxo_completo_cimento(self, admin_user, empresa_a, categoria, unidade):
        prod, f_kg, f_saco = self._setup(empresa_a, admin_user, categoria, unidade)

        entrada_estoque(user=admin_user, produto=prod, quantidade=Decimal("500"),
                        forma_venda=f_saco, quantidade_informada=Decimal("10"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("500.000")

        saida_estoque(user=admin_user, produto=prod, quantidade=Decimal("25"),
                      forma_venda=f_kg, quantidade_informada=Decimal("25"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("475.000")

        saida_estoque(user=admin_user, produto=prod, quantidade=Decimal("50"),
                      forma_venda=f_saco, quantidade_informada=Decimal("1"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("425.000")


# ──────────────────────────────────────────────
# QA BLOCO
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestQABloco:
    """
    Produto: Bloco Cerâmico
    Unidade base: Unidade
    Formas de venda: Unidade (×1), Milheiro (×1000)
    """

    def _setup(self, empresa, user, categoria, unidade_un):
        prod = make_produto(
            empresa, categoria=categoria, unidade=unidade_un,
            nome="Bloco Cerâmico", sku="BLOCO-01", codigo_barras="003",
            estoque_atual=Decimal("0.000"),
        )
        f_un = forma(empresa, prod, "Unidade", "UN", "UN", Decimal("1"), padrao=True)
        f_mil = forma(empresa, prod, "Milheiro", "MIL", "MIL", Decimal("1000"))
        return prod, f_un, f_mil

    def test_entrada_2_milheiros_resulta_2000_unidades(self, admin_user, empresa_a,
                                                        categoria, unidade):
        prod, f_un, f_mil = self._setup(empresa_a, admin_user, categoria, unidade)

        entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("2000.000"),
            forma_venda=f_mil, quantidade_informada=Decimal("2.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("2000.000")

    def test_venda_300_unidades(self, admin_user, empresa_a, categoria, unidade):
        prod, f_un, f_mil = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("2000.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("300.000"),
            forma_venda=f_un, quantidade_informada=Decimal("300.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("1700.000")

    def test_fluxo_completo_bloco(self, admin_user, empresa_a, categoria, unidade):
        prod, f_un, f_mil = self._setup(empresa_a, admin_user, categoria, unidade)

        entrada_estoque(user=admin_user, produto=prod, quantidade=Decimal("2000"),
                        forma_venda=f_mil, quantidade_informada=Decimal("2"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("2000.000")

        saida_estoque(user=admin_user, produto=prod, quantidade=Decimal("300"),
                      forma_venda=f_un, quantidade_informada=Decimal("300"))
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("1700.000")

    def test_venda_1_milheiro_resulta_1000_unidades(self, admin_user, empresa_a,
                                                    categoria, unidade):
        prod, f_un, f_mil = self._setup(empresa_a, admin_user, categoria, unidade)
        set_estoque(prod, Decimal("2000.000"))

        saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("1.000"),
            forma_venda=f_mil, quantidade_informada=Decimal("1.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("1000.000")


# ──────────────────────────────────────────────
# QA FERRO
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestQAFerro:
    """
    Produto: Ferro 10mm
    Unidade base: Metro
    Formas: Metro (×1), Barra 12m (×12)
    """

    def _setup(self, empresa, user, categoria, unidade_metro):
        prod = make_produto(
            empresa, categoria=categoria, unidade=unidade_metro,
            nome="Ferro 10mm", sku="FER-10", codigo_barras="004",
            estoque_atual=Decimal("0.000"),
        )
        f_metro = forma(empresa, prod, "Metro", "M", "M", Decimal("1"), padrao=True)
        f_barra = forma(empresa, prod, "Barra 12m", "BARRA", "BARRA", Decimal("12"))
        return prod, f_metro, f_barra

    def test_entrada_5_barras_resulta_60_metros(self, admin_user, empresa_a, categoria, unidade):
        prod, f_metro, f_barra = self._setup(empresa_a, admin_user, categoria, unidade)

        entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("60.000"),
            forma_venda=f_barra, quantidade_informada=Decimal("5.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("60.000")

    def test_movimentacao_snapshot_inclui_forma_venda(self, admin_user, empresa_a,
                                                        categoria, unidade):
        from apps.estoque.services.movimentacao import movimentacao_snapshot
        prod, f_metro, f_barra = self._setup(empresa_a, admin_user, categoria, unidade)

        mov = entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("60.000"),
            forma_venda=f_barra, quantidade_informada=Decimal("5.000"),
        )
        snap = movimentacao_snapshot(mov)
        assert snap["forma_venda_id"] == str(f_barra.pk)
        assert snap["quantidade_informada"] == "5.000"


# ──────────────────────────────────────────────
# Auditoria: quantidade_delta é a fonte da verdade
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestAuditoriaConversao:
    """Garante que quantidade_delta (unidade base) é sempre a fonte da verdade.
    quantidade_informada é apenas metadado — nunca movimenta saldo."""

    def test_quantidade_delta_eh_sempre_unidade_base(self, admin_user, empresa_a,
                                                       categoria, unidade):
        prod = make_produto(empresa_a, categoria=categoria, unidade=unidade,
                            nome="Produto Auditoria", sku="AUD-01", codigo_barras="A01",
                            estoque_atual=Decimal("0.000"))
        f_rolo = forma(empresa_a, prod, "Rolo 100m", "ROLO", "ROLO", Decimal("100"), padrao=True)

        mov = entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("300.000"),    # 3 rolos convertidos
            forma_venda=f_rolo,
            quantidade_informada=Decimal("3.000"),  # qtd informada (rolos)
        )
        assert mov.quantidade_delta == Decimal("300.000")     # unidade base: metros
        assert mov.quantidade_informada == Decimal("3.000")    # metadado: rolos
        assert mov.quantidade_convertida == Decimal("300.000") # property

    def test_quantidade_informada_nao_afeta_saldo(self, admin_user, empresa_a,
                                                    categoria, unidade):
        prod = make_produto(empresa_a, categoria=categoria, unidade=unidade,
                            nome="Produto Saldo", sku="SAL-01", codigo_barras="S01",
                            estoque_atual=Decimal("0.000"))
        f_saco = forma(empresa_a, prod, "Saco 50kg", "SACO", "SACO", Decimal("50"), padrao=True)

        entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("500.000"),    # convertido = 500 kg
            forma_venda=f_saco,
            quantidade_informada=Decimal("10.000"),  # metadado = 10 sacos
        )
        prod.refresh_from_db()
        # Saldo deve ser 500 (kg), NÃO 10 (sacos)
        assert prod.estoque_atual == Decimal("500.000")

    def test_movimentacao_sem_forma_usa_quantidade_direta(self, admin_user, empresa_a,
                                                           categoria, unidade):
        prod = make_produto(empresa_a, categoria=categoria, unidade=unidade,
                            nome="Produto Direto", sku="DIR-01", codigo_barras="D01",
                            estoque_atual=Decimal("0.000"))

        mov = entrada_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("50.000"),
        )
        assert mov.forma_venda_id is None
        assert mov.quantidade_informada is None
        assert mov.quantidade_delta == Decimal("50.000")

    def test_cancelamento_mantem_consistencia(self, admin_user, empresa_a, categoria, unidade):
        from apps.estoque.services import cancelar_movimentacao
        prod = make_produto(empresa_a, categoria=categoria, unidade=unidade,
                            nome="Produto Cancel", sku="CAN-01", codigo_barras="C01",
                            estoque_atual=Decimal("1000.000"))
        f_rolo = forma(empresa_a, prod, "Rolo", "ROLO", "ROLO", Decimal("100"), padrao=True)

        mov = saida_estoque(
            user=admin_user, produto=prod,
            quantidade=Decimal("200.000"),
            forma_venda=f_rolo, quantidade_informada=Decimal("2.000"),
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("800.000")

        cancelar_movimentacao(
            user=admin_user, movimentacao=mov,
            motivo="Cancelamento QA",
        )
        prod.refresh_from_db()
        assert prod.estoque_atual == Decimal("1000.000")
