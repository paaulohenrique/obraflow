"""Testes de integração: FormaVendaProduto + NF-e (revisão, confirmação, conversão, segurança)."""
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.estoque.models import FormaVendaProduto, MovimentacaoEstoque
from apps.notas_entrada.models import (
    HistoricoNotaFiscalEntrada,
    ItemNotaFiscalEntrada,
    NotaFiscalEntrada,
)
from apps.notas_entrada.services.confirmacao import confirmar_nota
from apps.notas_entrada.services.nota import vincular_produto_item

from .conftest import xml_file


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def make_forma(empresa, produto, nome, codigo, unidade_sigla, fator,
               padrao=False, ativo=True):
    return FormaVendaProduto.objects.create(
        company=empresa,
        produto=produto,
        nome=nome,
        codigo=codigo,
        unidade=unidade_sigla,
        fator_conversao=fator,
        preco_venda=Decimal("0.00"),
        ativo=ativo,
        padrao=padrao,
        permite_fracionado=True,
    )


def importar_nota(admin_user):
    from apps.notas_entrada.services.nota import importar_xml_nota
    return importar_xml_nota(user=admin_user, arquivo=xml_file())


# ──────────────────────────────────────────────
# Vincular produto + forma_venda durante revisão
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestVincularFormaVenda:
    def test_vincular_produto_e_forma_venda(self, admin_user, empresa_a,
                                             produto_cimento, fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()
        assert item is not None

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)

        resultado = vincular_produto_item(
            user=admin_user,
            item=item,
            produto=produto_cimento,
            forma_venda=f_saco,
        )
        resultado.refresh_from_db()
        assert resultado.produto_id == produto_cimento.pk
        assert resultado.forma_venda_id == f_saco.pk

    def test_alterar_forma_venda_sem_mudar_produto(self, admin_user, empresa_a,
                                                     produto_cimento, fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)
        f_kg = make_forma(empresa_a, produto_cimento, "Kg", "KG", "KG", Decimal("1"))

        # Vincula produto + saco
        vincular_produto_item(user=admin_user, item=item, produto=produto_cimento,
                               forma_venda=f_saco)
        item.refresh_from_db()
        assert item.forma_venda_id == f_saco.pk

        # Muda para Kg sem alterar produto
        vincular_produto_item(user=admin_user, item=item, produto=item.produto,
                               forma_venda=f_kg)
        item.refresh_from_db()
        assert item.forma_venda_id == f_kg.pk

    def test_limpar_forma_venda_enviando_null(self, admin_user, empresa_a,
                                               produto_cimento, fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)
        vincular_produto_item(user=admin_user, item=item, produto=produto_cimento,
                               forma_venda=f_saco)
        item.refresh_from_db()
        assert item.forma_venda_id is not None

        # Limpa forma_venda
        vincular_produto_item(user=admin_user, item=item, produto=item.produto,
                               forma_venda=None)
        item.refresh_from_db()
        assert item.forma_venda_id is None

    def test_mudanca_produto_limpa_forma_automaticamente(self, admin_user, empresa_a,
                                                          produto_cimento, produto_sem_ean,
                                                          fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco", "SACO", "SACO",
                             Decimal("50"), padrao=True)
        vincular_produto_item(user=admin_user, item=item, produto=produto_cimento,
                               forma_venda=f_saco)
        item.refresh_from_db()
        assert item.forma_venda_id == f_saco.pk

        # Muda produto → forma_venda deve ser limpa automaticamente
        vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)
        item.refresh_from_db()
        assert item.forma_venda_id is None

    def test_forma_venda_sem_produto_rejeitada(self, admin_user, empresa_a,
                                                produto_cimento, fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco", "SACO", "SACO",
                             Decimal("50"), padrao=True)

        with pytest.raises(ValidationError, match="produto"):
            vincular_produto_item(user=admin_user, item=item, forma_venda=f_saco)


# ──────────────────────────────────────────────
# Confirmação com conversão de unidade
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestConfirmacaoComFormaVenda:
    def _ignorar_todos_exceto(self, user, nota, item_pk):
        """Marca todos os outros itens como ignorados para isolar o teste."""
        for outro in ItemNotaFiscalEntrada.objects.filter(
            nota=nota, ignorado=False, deleted_at__isnull=True
        ).exclude(pk=item_pk):
            vincular_produto_item(user=user, item=outro, ignorado=True)

    def test_confirmacao_converte_quantidade_corretamente(
        self, admin_user, empresa_a, produto_cimento, fornecedor_a
    ):
        """
        Cenário: XML traz item X sacos. Saco 50kg. Confirmar deve entrar X*50 kg.
        Isolamos o teste ignorando todos os outros itens da NF-e.
        """
        nota = importar_nota(admin_user)
        # Pega qualquer item sem produto para vincular com forma_venda
        item = ItemNotaFiscalEntrada.objects.filter(
            nota=nota, produto__isnull=True
        ).first()
        assert item is not None, "Esperava item sem produto auto-linkado"

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)

        # Ignora TODOS exceto o item de teste
        self._ignorar_todos_exceto(admin_user, nota, item.pk)

        # Vincula produto + forma
        vincular_produto_item(user=admin_user, item=item, produto=produto_cimento,
                               forma_venda=f_saco)
        item.refresh_from_db()

        produto_cimento.refresh_from_db()
        estoque_antes = produto_cimento.estoque_atual
        qtd_xml = item.quantidade

        nota_confirmada = confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert nota_confirmada.status == NotaFiscalEntrada.STATUS_CONFIRMADA

        item.refresh_from_db()
        assert item.movimentacao_estoque_id is not None

        mov = item.movimentacao_estoque
        assert mov.tipo == MovimentacaoEstoque.TIPO_ENTRADA
        assert mov.forma_venda_id == f_saco.pk
        assert mov.quantidade_informada == qtd_xml        # qtd bruta do XML
        assert mov.quantidade_delta == qtd_xml * Decimal("50")  # convertido

        produto_cimento.refresh_from_db()
        assert produto_cimento.estoque_atual == estoque_antes + qtd_xml * Decimal("50")

    def test_confirmacao_sem_forma_usa_quantidade_direta(
        self, admin_user, empresa_a, produto_cimento, fornecedor_a
    ):
        """Sem forma_venda, quantidade entra diretamente (sem conversão)."""
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(
            nota=nota, produto__isnull=True
        ).first()
        assert item is not None

        self._ignorar_todos_exceto(admin_user, nota, item.pk)
        vincular_produto_item(user=admin_user, item=item, produto=produto_cimento)

        produto_cimento.refresh_from_db()
        estoque_antes = produto_cimento.estoque_atual
        qtd_xml = item.quantidade

        confirmar_nota(user=admin_user, nota_id=nota.pk)

        produto_cimento.refresh_from_db()
        assert produto_cimento.estoque_atual == estoque_antes + qtd_xml

        item.refresh_from_db()
        mov = item.movimentacao_estoque
        assert mov.forma_venda_id is None
        assert mov.quantidade_informada is None
        assert mov.quantidade_delta == qtd_xml


# ──────────────────────────────────────────────
# Segurança
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestSegurancaFormaVendaNFe:
    def test_forma_venda_outro_produto_rejeitada(self, admin_user, empresa_a,
                                                  produto_cimento, produto_sem_ean,
                                                  fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        # Forma de venda de outro produto
        f_outro = make_forma(empresa_a, produto_sem_ean, "UN", "UN", "UN",
                              Decimal("1"), padrao=True)

        with pytest.raises(ValidationError, match="produto"):
            vincular_produto_item(user=admin_user, item=item,
                                   produto=produto_cimento, forma_venda=f_outro)

    def test_forma_venda_inativa_rejeitada(self, admin_user, empresa_a,
                                            produto_cimento, fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        # Cria uma forma ativa para poder ter uma inativa coexistindo
        make_forma(empresa_a, produto_cimento, "Ativa", "ATIVA", "KG",
                    Decimal("1"), padrao=True, ativo=True)
        f_inativa = make_forma(empresa_a, produto_cimento, "Inativa", "INATIVO", "SACO",
                                Decimal("50"), padrao=False, ativo=False)

        with pytest.raises(ValidationError, match="inativa"):
            vincular_produto_item(user=admin_user, item=item,
                                   produto=produto_cimento, forma_venda=f_inativa)

    def test_forma_venda_outra_empresa_rejeitada(self, admin_user, empresa_a, empresa_b,
                                                   produto_cimento, produto_sem_ean,
                                                   fornecedor_a, user_b):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        # Forma de outra empresa
        from apps.estoque.models import CategoriaProduto, UnidadeMedida
        unidade_b = UnidadeMedida.objects.create(company=empresa_b, nome="UN B", sigla="UNB")
        cat_b = CategoriaProduto.objects.create(company=empresa_b, nome="Cat B")
        from apps.estoque.models import Produto as ProdutoModel
        from apps.empresas.validators import clean_cnpj
        prod_b = ProdutoModel.objects.create(
            company=empresa_b, nome="Prod B", sku="B-001", codigo_barras="B001",
            categoria=cat_b, unidade=unidade_b, preco_compra=Decimal("1"),
            preco_venda=Decimal("2"),
        )
        f_b = make_forma(empresa_b, prod_b, "UN B", "UNB", "UNB", Decimal("1"), padrao=True)

        with pytest.raises(ValidationError, match="empresa"):
            vincular_produto_item(user=admin_user, item=item,
                                   produto=produto_cimento, forma_venda=f_b)


# ──────────────────────────────────────────────
# API — endpoint PATCH /itens/{id}/
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestAPIVincularFormaVendaItem:
    def _url(self, nota_pk, item_pk):
        return f"/api/v1/notas-entrada/{nota_pk}/itens/{item_pk}/"

    def test_patch_forma_venda_sucesso(self, admin_client, admin_user, empresa_a,
                                        produto_cimento, fornecedor_a):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)

        payload = {"produto": str(produto_cimento.pk), "forma_venda": str(f_saco.pk)}
        resp = admin_client.patch(self._url(nota.pk, item.pk), payload, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert str(resp.data["forma_venda"]) == str(f_saco.pk)
        assert resp.data["forma_venda_nome"] == "Saco 50kg"
        assert resp.data["forma_venda_fator"] == "50.000000"

    def test_patch_forma_venda_exibe_quantidade_convertida(
        self, admin_client, admin_user, empresa_a, produto_cimento, fornecedor_a
    ):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)

        resp = admin_client.patch(
            self._url(nota.pk, item.pk),
            {"produto": str(produto_cimento.pk), "forma_venda": str(f_saco.pk)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        qtd_xml = Decimal(str(item.quantidade))
        qtd_convertida = Decimal(resp.data["quantidade_convertida"])
        assert qtd_convertida == qtd_xml * Decimal("50")

    def test_patch_forma_venda_produto_errado_rejeitado(
        self, admin_client, admin_user, empresa_a,
        produto_cimento, produto_sem_ean, fornecedor_a
    ):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_outro = make_forma(empresa_a, produto_sem_ean, "UN", "UN", "UN",
                              Decimal("1"), padrao=True)

        resp = admin_client.patch(
            self._url(nota.pk, item.pk),
            {"produto": str(produto_cimento.pk), "forma_venda": str(f_outro.pk)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_forma_venda_inativa_rejeitada(
        self, admin_client, admin_user, empresa_a, produto_cimento, fornecedor_a
    ):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        make_forma(empresa_a, produto_cimento, "Ativa", "ATIVA", "KG",
                    Decimal("1"), padrao=True, ativo=True)
        f_inativa = make_forma(empresa_a, produto_cimento, "Inativa", "INATIVO", "SACO",
                                Decimal("50"), padrao=False, ativo=False)

        resp = admin_client.patch(
            self._url(nota.pk, item.pk),
            {"produto": str(produto_cimento.pk), "forma_venda": str(f_inativa.pk)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_sem_forma_venda_mantém_campo_null(
        self, admin_client, admin_user, empresa_a, produto_cimento, fornecedor_a
    ):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        resp = admin_client.patch(
            self._url(nota.pk, item.pk),
            {"produto": str(produto_cimento.pk)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["forma_venda"] is None
        assert resp.data["forma_venda_nome"] is None
        assert resp.data["quantidade_convertida"] is None

    def test_listar_itens_inclui_campos_forma_venda(
        self, admin_client, admin_user, empresa_a, produto_cimento, fornecedor_a
    ):
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        f_saco = make_forma(empresa_a, produto_cimento, "Saco 50kg", "SACO", "SACO",
                             Decimal("50"), padrao=True)
        admin_client.patch(
            self._url(nota.pk, item.pk),
            {"produto": str(produto_cimento.pk), "forma_venda": str(f_saco.pk)},
            format="json",
        )

        resp = admin_client.get(f"/api/v1/notas-entrada/{nota.pk}/itens/")
        assert resp.status_code == status.HTTP_200_OK
        itens = resp.data["results"]
        item_resp = next(i for i in itens if str(i["id"]) == str(item.pk))
        assert "forma_venda" in item_resp
        assert "forma_venda_nome" in item_resp
        assert "quantidade_convertida" in item_resp


# ──────────────────────────────────────────────
# Multi-tenant
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestMultiTenantFormaVendaNFe:
    def test_forma_venda_outra_empresa_nao_visivel_no_serializer(
        self, admin_client, admin_user, empresa_a, empresa_b,
        produto_cimento, fornecedor_a, user_b
    ):
        """Serializer TenantScoped filtra forma_venda por empresa."""
        nota = importar_nota(admin_user)
        item = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True).first()

        from apps.estoque.models import CategoriaProduto, UnidadeMedida, Produto as ProdModel
        unidade_b = UnidadeMedida.objects.create(company=empresa_b, nome="UN B2", sigla="UB2")
        cat_b = CategoriaProduto.objects.create(company=empresa_b, nome="Cat B2")
        prod_b = ProdModel.objects.create(
            company=empresa_b, nome="Prod B2", sku="B-002", codigo_barras="B002",
            categoria=cat_b, unidade=unidade_b, preco_compra=Decimal("1"),
            preco_venda=Decimal("2"),
        )
        f_b = make_forma(empresa_b, prod_b, "UN B2", "UB2", "UB2", Decimal("1"), padrao=True)

        resp = admin_client.patch(
            f"/api/v1/notas-entrada/{nota.pk}/itens/{item.pk}/",
            {"produto": str(produto_cimento.pk), "forma_venda": str(f_b.pk)},
            format="json",
        )
        # Forma de outra empresa não está no queryset → 400
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
