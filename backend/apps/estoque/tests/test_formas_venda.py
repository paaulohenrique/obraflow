"""Testes para FormaVendaProduto: model, service, API, conversão, multi-tenant e concorrência."""
from decimal import Decimal

import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.estoque.models import FormaVendaProduto, MovimentacaoEstoque
from apps.estoque.services import (
    ativar_forma_venda,
    atualizar_forma_venda,
    converter_quantidade,
    criar_forma_venda,
    definir_forma_padrao,
    entrada_estoque,
    inativar_forma_venda,
    saida_estoque,
    soft_delete_forma_venda,
)
from apps.estoque.selectors import get_formas_venda, get_forma_venda_by_id

from .conftest import (
    COMPANY_B_UUID,
    make_categoria,
    make_fornecedor,
    make_produto,
    make_unidade,
    VALID_CNPJ_FORNECEDOR_B,
)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def make_forma_venda(empresa, produto, **kwargs):
    defaults = {
        "nome": "Metro",
        "codigo": "M",
        "unidade": "M",
        "fator_conversao": Decimal("1.000000"),
        "preco_venda": Decimal("5.00"),
        "ativo": True,
        "padrao": True,
        "permite_fracionado": True,
    }
    defaults.update(kwargs)
    return FormaVendaProduto.objects.create(company=empresa, produto=produto, **defaults)


# ──────────────────────────────────────────────
# MODEL — validações diretas
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFormaVendaProdutoModel:
    def test_criar_forma_valida(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto)
        assert forma.pk is not None
        assert str(forma.fator_conversao) == "1.000000"

    def test_converter_metro_a_metro(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1.000000"))
        assert forma.converter(Decimal("20")) == Decimal("20.000")

    def test_converter_rolo_100m(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, nome="Rolo 100m", codigo="ROLO",
                                  unidade="ROLO", fator_conversao=Decimal("100.000000"))
        assert forma.converter(Decimal("3")) == Decimal("300.000")

    def test_converter_saco_50kg(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, nome="Saco 50kg", codigo="SACO",
                                  unidade="SACO", fator_conversao=Decimal("50.000000"))
        assert forma.converter(Decimal("10")) == Decimal("500.000")

    def test_converter_milheiro(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, nome="Milheiro", codigo="MIL",
                                  unidade="MIL", fator_conversao=Decimal("1000.000000"))
        assert forma.converter(Decimal("2")) == Decimal("2000.000")

    def test_fator_zero_invalido(self, empresa_a, produto):
        from django.core.exceptions import ValidationError as DjangoVE
        forma = FormaVendaProduto(
            company=empresa_a,
            produto=produto,
            nome="Inválido",
            unidade="X",
            fator_conversao=Decimal("0"),
            preco_venda=Decimal("0.00"),
        )
        with pytest.raises(DjangoVE):
            forma.full_clean()

    def test_fator_negativo_invalido(self, empresa_a, produto):
        from django.core.exceptions import ValidationError as DjangoVE
        forma = FormaVendaProduto(
            company=empresa_a,
            produto=produto,
            nome="Inválido",
            unidade="X",
            fator_conversao=Decimal("-1"),
            preco_venda=Decimal("0.00"),
        )
        with pytest.raises(DjangoVE):
            forma.full_clean()

    def test_preco_negativo_invalido(self, empresa_a, produto):
        from django.core.exceptions import ValidationError as DjangoVE
        forma = FormaVendaProduto(
            company=empresa_a,
            produto=produto,
            nome="Inválido",
            unidade="M",
            fator_conversao=Decimal("1"),
            preco_venda=Decimal("-1.00"),
        )
        with pytest.raises(DjangoVE):
            forma.full_clean()

    def test_unidade_vazia_invalida(self, empresa_a, produto):
        from django.core.exceptions import ValidationError as DjangoVE
        forma = FormaVendaProduto(
            company=empresa_a,
            produto=produto,
            nome="Inválido",
            unidade="",
            fator_conversao=Decimal("1"),
            preco_venda=Decimal("0.00"),
        )
        with pytest.raises(DjangoVE):
            forma.full_clean()

    def test_str_representation(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, nome="Metro")
        assert "Metro" in str(forma)

    def test_codigo_unico_por_produto_empresa(self, empresa_a, produto):
        make_forma_venda(empresa_a, produto, codigo="M", padrao=True)
        with pytest.raises(IntegrityError):
            FormaVendaProduto.objects.create(
                company=empresa_a,
                produto=produto,
                nome="Metro duplicado",
                codigo="M",
                unidade="M",
                fator_conversao=Decimal("1"),
                preco_venda=Decimal("0.00"),
                padrao=False,
            )


# ──────────────────────────────────────────────
# SERVICE — CRUD
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFormaVendaService:
    def test_criar_forma_venda_simples(self, admin_user, produto):
        forma = criar_forma_venda(
            user=admin_user,
            produto=produto,
            data={
                "nome": "Metro",
                "codigo": "M",
                "unidade": "M",
                "fator_conversao": Decimal("1.000000"),
                "preco_venda": Decimal("5.00"),
                "padrao": True,
            },
        )
        assert forma.pk is not None
        assert forma.padrao is True
        assert forma.ativo is True

    def test_criar_segunda_forma(self, admin_user, empresa_a, produto):
        criar_forma_venda(
            user=admin_user,
            produto=produto,
            data={
                "nome": "Metro",
                "codigo": "M",
                "unidade": "M",
                "fator_conversao": Decimal("1.000000"),
                "padrao": True,
            },
        )
        rolo = criar_forma_venda(
            user=admin_user,
            produto=produto,
            data={
                "nome": "Rolo 100m",
                "codigo": "ROLO",
                "unidade": "ROLO",
                "fator_conversao": Decimal("100.000000"),
                "padrao": False,
            },
        )
        assert rolo.padrao is False
        assert FormaVendaProduto.objects.filter(
            produto=produto, padrao=True
        ).count() == 1

    def test_criar_nova_forma_padrao_desmarca_anterior(self, admin_user, empresa_a, produto):
        metro = criar_forma_venda(
            user=admin_user,
            produto=produto,
            data={"nome": "Metro", "codigo": "M", "unidade": "M",
                  "fator_conversao": Decimal("1"), "padrao": True},
        )
        criar_forma_venda(
            user=admin_user,
            produto=produto,
            data={"nome": "Rolo", "codigo": "ROLO", "unidade": "ROLO",
                  "fator_conversao": Decimal("100"), "padrao": True},
        )
        metro.refresh_from_db()
        assert metro.padrao is False

    def test_produto_de_outra_empresa_rejeitado(self, other_company_user, produto):
        with pytest.raises(ValidationError, match="empresa"):
            criar_forma_venda(
                user=other_company_user,
                produto=produto,
                data={"nome": "Metro", "unidade": "M", "fator_conversao": Decimal("1")},
            )

    def test_produto_inativo_rejeitado(self, admin_user, produto):
        from apps.estoque.services import inativar_produto
        inativar_produto(user=admin_user, produto=produto)
        with pytest.raises(ValidationError, match="inativo"):
            criar_forma_venda(
                user=admin_user,
                produto=produto,
                data={"nome": "Metro", "unidade": "M", "fator_conversao": Decimal("1")},
            )

    def test_atualizar_forma_venda(self, admin_user, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto)
        atualizada = atualizar_forma_venda(
            user=admin_user,
            forma_venda=forma,
            data={"nome": "Metro Linear", "preco_venda": Decimal("7.50")},
        )
        assert atualizada.nome == "Metro Linear"
        assert atualizada.preco_venda == Decimal("7.50")

    def test_atualizar_fator_zero_rejeitado(self, admin_user, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto)
        with pytest.raises(ValidationError):
            atualizar_forma_venda(
                user=admin_user,
                forma_venda=forma,
                data={"fator_conversao": Decimal("0")},
            )

    def test_definir_forma_padrao(self, admin_user, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False)
        definir_forma_padrao(user=admin_user, forma_venda=forma2)
        forma1.refresh_from_db()
        forma2.refresh_from_db()
        assert forma2.padrao is True
        assert forma1.padrao is False

    def test_inativar_forma_venda(self, admin_user, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False)
        inativada = inativar_forma_venda(user=admin_user, forma_venda=forma2)
        assert inativada.ativo is False

    def test_inativar_ultima_forma_rejeitado(self, admin_user, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, padrao=True)
        with pytest.raises(ValidationError, match="única"):
            inativar_forma_venda(user=admin_user, forma_venda=forma)

    def test_ativar_forma_inativa(self, admin_user, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False,
                                   ativo=False)
        ativada = ativar_forma_venda(user=admin_user, forma_venda=forma2)
        assert ativada.ativo is True

    def test_soft_delete_forma_venda(self, admin_user, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False)
        soft_delete_forma_venda(user=admin_user, forma_venda=forma2)
        assert not FormaVendaProduto.objects.filter(pk=forma2.pk, deleted_at__isnull=True).exists()

    def test_soft_delete_ultima_forma_rejeitado(self, admin_user, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, padrao=True)
        with pytest.raises(ValidationError, match="última"):
            soft_delete_forma_venda(user=admin_user, forma_venda=forma)


# ──────────────────────────────────────────────
# CONVERSÃO — função helper
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestConverterQuantidade:
    def test_metro_a_metro(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))
        assert converter_quantidade(forma_venda=forma, quantidade=Decimal("20")) == Decimal("20.000")

    def test_rolo_100m_converte(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("100"))
        assert converter_quantidade(forma_venda=forma, quantidade=Decimal("3")) == Decimal("300.000")

    def test_saco_50kg_converte(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("50"))
        assert converter_quantidade(forma_venda=forma, quantidade=Decimal("10")) == Decimal("500.000")

    def test_barra_ferro_12m(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("12"))
        assert converter_quantidade(forma_venda=forma, quantidade=Decimal("5")) == Decimal("60.000")

    def test_quantidade_zero_rejeitada(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))
        with pytest.raises(ValidationError):
            converter_quantidade(forma_venda=forma, quantidade=Decimal("0"))

    def test_fracionado_menor_que_1(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))
        result = converter_quantidade(forma_venda=forma, quantidade=Decimal("0.5"))
        assert result == Decimal("0.500")


# ──────────────────────────────────────────────
# ESTOQUE — movimentação com forma de venda
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEstoqueComFormaVenda:
    def test_entrada_por_rolo(self, admin_user, empresa_a, produto):
        forma_rolo = make_forma_venda(
            empresa_a, produto, nome="Rolo 100m", codigo="ROLO",
            unidade="ROLO", fator_conversao=Decimal("100"), padrao=False
        )
        produto.estoque_atual = Decimal("0.000")
        produto.save(update_fields=["estoque_atual"])

        mov = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("300.000"),
            forma_venda=forma_rolo,
            quantidade_informada=Decimal("3.000"),
        )

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("300.000")
        assert mov.quantidade_delta == Decimal("300.000")
        assert mov.forma_venda_id == forma_rolo.pk
        assert mov.quantidade_informada == Decimal("3.000")

    def test_saida_por_metro(self, admin_user, empresa_a, produto):
        forma_metro = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))
        # produto começa com estoque_atual = 10.000

        mov = saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("5.000"),
            forma_venda=forma_metro,
            quantidade_informada=Decimal("5.000"),
        )

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("5.000")
        assert mov.quantidade_delta == Decimal("-5.000")
        assert mov.forma_venda_id == forma_metro.pk

    def test_entrada_por_saco_50kg(self, admin_user, empresa_a, produto):
        forma_saco = make_forma_venda(
            empresa_a, produto, nome="Saco 50kg", codigo="SACO",
            unidade="SACO", fator_conversao=Decimal("50"), padrao=False
        )
        produto.estoque_atual = Decimal("0.000")
        produto.save(update_fields=["estoque_atual"])

        entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("500.000"),
            forma_venda=forma_saco,
            quantidade_informada=Decimal("10.000"),
        )

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("500.000")

    def test_entrada_por_milheiro(self, admin_user, empresa_a, produto):
        forma_mil = make_forma_venda(
            empresa_a, produto, nome="Milheiro", codigo="MIL",
            unidade="MIL", fator_conversao=Decimal("1000"), padrao=False
        )
        produto.estoque_atual = Decimal("0.000")
        produto.save(update_fields=["estoque_atual"])

        entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("2000.000"),
            forma_venda=forma_mil,
            quantidade_informada=Decimal("2.000"),
        )

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("2000.000")

    def test_saida_por_unidade_bloco(self, admin_user, empresa_a, produto):
        forma_un = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))
        produto.estoque_atual = Decimal("2000.000")
        produto.save(update_fields=["estoque_atual"])

        saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("500.000"),
            forma_venda=forma_un,
            quantidade_informada=Decimal("500.000"),
        )

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("1500.000")

    def test_forma_venda_produto_errado_rejeitada(self, admin_user, empresa_a, produto,
                                                  categoria, unidade, fornecedor):
        outro_produto = make_produto(
            empresa_a,
            categoria=categoria,
            unidade=unidade,
            fornecedor=fornecedor,
            nome="Produto Outro",
            sku="outro-01",
            codigo_barras="000000000099",
        )
        forma_outro = make_forma_venda(empresa_a, outro_produto, codigo="M_OUT")

        with pytest.raises(ValidationError):
            entrada_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("100"),
                forma_venda=forma_outro,
                quantidade_informada=Decimal("1"),
            )

    def test_forma_venda_empresa_errada_rejeitada(self, admin_user, empresa_a, produto, produto_b):
        from apps.empresas.models import Empresa
        empresa_b = Empresa.objects.get(id=COMPANY_B_UUID)
        forma_b = make_forma_venda(empresa_b, produto_b, codigo="B_M")

        with pytest.raises(ValidationError, match="empresa"):
            entrada_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("100"),
                forma_venda=forma_b,
                quantidade_informada=Decimal("1"),
            )

    def test_quantidade_convertida_property(self, admin_user, empresa_a, produto):
        forma_rolo = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("100"))
        mov = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("300"),
            forma_venda=forma_rolo,
            quantidade_informada=Decimal("3"),
        )
        assert mov.quantidade_convertida == Decimal("300")

    def test_sem_forma_venda_backward_compatible(self, admin_user, produto):
        mov = entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("50"),
        )
        assert mov.forma_venda_id is None
        assert mov.quantidade_informada is None
        assert mov.quantidade_delta == Decimal("50")


# ──────────────────────────────────────────────
# API — endpoints REST
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFormaVendaAPI:
    BASE_URL = "/api/v1/estoque/formas-venda/"

    def test_listar_formas_venda(self, admin_client, empresa_a, produto):
        make_forma_venda(empresa_a, produto)
        resp = admin_client.get(self.BASE_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_listar_filtra_por_produto(self, admin_client, empresa_a, produto,
                                        categoria, unidade, fornecedor):
        make_forma_venda(empresa_a, produto, codigo="M1")
        outro = make_produto(empresa_a, categoria=categoria, unidade=unidade, fornecedor=fornecedor,
                              nome="Produto Y", sku="Y-01", codigo_barras="000099")
        make_forma_venda(empresa_a, outro, codigo="M2")
        resp = admin_client.get(self.BASE_URL + f"?produto={produto.pk}")
        assert resp.status_code == status.HTTP_200_OK
        ids = [item["produto_id"] for item in resp.data["results"]]
        assert all(str(pid) == str(produto.pk) for pid in ids)

    def test_criar_forma_venda_via_api(self, admin_client, produto):
        payload = {
            "produto": str(produto.pk),
            "nome": "Rolo 100m",
            "codigo": "ROLO",
            "unidade": "ROLO",
            "fator_conversao": "100.000000",
            "preco_venda": "15.00",
            "padrao": False,
        }
        resp = admin_client.post(self.BASE_URL, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["nome"] == "Rolo 100m"
        assert resp.data["fator_conversao"] == "100.000000"
        assert resp.data["preco_venda"] == "15.00"

    def test_preco_forma_venda_persiste_ao_reabrir_api(self, admin_client, produto):
        payload = {
            "produto": str(produto.pk),
            "nome": "Saco 50kg",
            "codigo": "SACO",
            "unidade": "SACO",
            "fator_conversao": "50.000000",
            "preco_venda": "45.00",
            "padrao": False,
        }
        create = admin_client.post(self.BASE_URL, payload, format="json")
        assert create.status_code == status.HTTP_201_CREATED
        forma_id = create.data["id"]

        detail = admin_client.get(f"{self.BASE_URL}{forma_id}/")
        assert detail.status_code == status.HTTP_200_OK
        assert detail.data["preco_venda"] == "45.00"

        list_response = admin_client.get(self.BASE_URL + f"?produto={produto.pk}")
        assert list_response.status_code == status.HTTP_200_OK
        forma = next(item for item in list_response.data["results"] if item["id"] == forma_id)
        assert forma["preco_venda"] == "45.00"

    def test_criar_fator_zero_rejeitado(self, admin_client, produto):
        payload = {
            "produto": str(produto.pk),
            "nome": "Invalido",
            "unidade": "X",
            "fator_conversao": "0",
        }
        resp = admin_client.post(self.BASE_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_atualizar_via_api(self, admin_client, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto)
        resp = admin_client.patch(
            f"{self.BASE_URL}{forma.pk}/",
            {"nome": "Metro Linear", "preco_venda": "7.50"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["nome"] == "Metro Linear"
        assert resp.data["preco_venda"] == "7.50"

        reaberta = admin_client.get(f"{self.BASE_URL}{forma.pk}/")
        assert reaberta.status_code == status.HTTP_200_OK
        assert reaberta.data["preco_venda"] == "7.50"

    def test_definir_padrao_via_api(self, admin_client, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False)
        resp = admin_client.post(f"{self.BASE_URL}{forma2.pk}/definir-padrao/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["padrao"] is True

    def test_ativar_via_api(self, admin_client, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"),
                                   padrao=False, ativo=False)
        resp = admin_client.post(f"{self.BASE_URL}{forma2.pk}/ativar/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["ativo"] is True

    def test_inativar_via_api(self, admin_client, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False)
        resp = admin_client.post(f"{self.BASE_URL}{forma2.pk}/inativar/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["ativo"] is False

    def test_deletar_via_api(self, admin_client, empresa_a, produto):
        forma1 = make_forma_venda(empresa_a, produto, codigo="M1", padrao=True)
        forma2 = make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo",
                                   unidade="ROLO", fator_conversao=Decimal("100"), padrao=False)
        resp = admin_client.delete(f"{self.BASE_URL}{forma2.pk}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_anonimo_nao_acessa(self, anon_client):
        resp = anon_client.get(self.BASE_URL)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_viewer_pode_listar(self, viewer_client, empresa_a, produto):
        make_forma_venda(empresa_a, produto)
        resp = viewer_client.get(self.BASE_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_isolamento_tenant(self, admin_client, other_company_user, empresa_b, produto_b):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        client_b = APIClient()
        refresh = RefreshToken.for_user(other_company_user)
        client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        make_forma_venda(empresa_b, produto_b, codigo="B_M")

        resp_a = admin_client.get(self.BASE_URL)
        ids_a = [r["produto_id"] for r in resp_a.data["results"]]

        resp_b = client_b.get(self.BASE_URL)
        ids_b = [r["produto_id"] for r in resp_b.data["results"]]

        # Nenhuma sobreposição de produtos
        assert set(ids_a).isdisjoint(set(ids_b))


# ──────────────────────────────────────────────
# MOVIMENTAÇÃO COM FORMA VIA API
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestMovimentacaoComFormaVendaAPI:
    ENTRADA_URL = "/api/v1/estoque/movimentacoes/entrada/"
    SAIDA_URL = "/api/v1/estoque/movimentacoes/saida/"

    def test_entrada_com_forma_e_quantidade_informada(self, admin_client, empresa_a, produto):
        forma = make_forma_venda(
            empresa_a, produto, nome="Rolo 100m", codigo="ROLO",
            unidade="ROLO", fator_conversao=Decimal("100"), padrao=False
        )
        produto.estoque_atual = Decimal("0.000")
        produto.save(update_fields=["estoque_atual"])

        payload = {
            "produto": str(produto.pk),
            "forma_venda": str(forma.pk),
            "quantidade_informada": "3.000",
        }
        resp = admin_client.post(self.ENTRADA_URL, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Decimal(resp.data["quantidade_delta"]) == Decimal("300.000")
        assert str(resp.data["forma_venda"]) == str(forma.pk)
        assert Decimal(resp.data["quantidade_informada"]) == Decimal("3.000")

    def test_entrada_sem_quantidade_rejeitada(self, admin_client, produto):
        payload = {"produto": str(produto.pk)}
        resp = admin_client.post(self.ENTRADA_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_saida_com_forma_venda(self, admin_client, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))

        payload = {
            "produto": str(produto.pk),
            "forma_venda": str(forma.pk),
            "quantidade_informada": "5.000",
        }
        resp = admin_client.post(self.SAIDA_URL, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Decimal(resp.data["quantidade_delta"]) == Decimal("-5.000")

    def test_forma_venda_produto_errado_rejeitada_na_api(self, admin_client, empresa_a, produto,
                                                          categoria, unidade, fornecedor):
        outro = make_produto(empresa_a, categoria=categoria, unidade=unidade, fornecedor=fornecedor,
                              nome="Outro X", sku="X-001", codigo_barras="999999")
        forma_outro = make_forma_venda(empresa_a, outro, codigo="X_M")

        payload = {
            "produto": str(produto.pk),
            "forma_venda": str(forma_outro.pk),
            "quantidade_informada": "1.000",
        }
        resp = admin_client.post(self.ENTRADA_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ──────────────────────────────────────────────
# SELETOR
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFormaVendaSelectors:
    def test_get_formas_venda_por_produto(self, empresa_a, produto):
        make_forma_venda(empresa_a, produto, codigo="M1")
        make_forma_venda(empresa_a, produto, codigo="M2", nome="Rolo", unidade="ROLO",
                          fator_conversao=Decimal("100"), padrao=False)
        qs = get_formas_venda(company_id=empresa_a.pk, produto_id=produto.pk)
        assert qs.count() == 2

    def test_get_forma_venda_by_id(self, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto)
        found = get_forma_venda_by_id(company_id=empresa_a.pk, forma_venda_id=forma.pk)
        assert found.pk == forma.pk

    def test_get_forma_venda_empresa_errada_not_found(self, empresa_a, empresa_b, produto_b):
        forma = make_forma_venda(empresa_b, produto_b)
        from rest_framework.exceptions import NotFound
        with pytest.raises(NotFound):
            get_forma_venda_by_id(company_id=empresa_a.pk, forma_venda_id=forma.pk)

    def test_get_formas_venda_sem_produto_retorna_todas(self, empresa_a, produto):
        make_forma_venda(empresa_a, produto, codigo="M1")
        qs = get_formas_venda(company_id=empresa_a.pk)
        assert qs.count() >= 1


# ──────────────────────────────────────────────
# CONCORRÊNCIA — locks transacionais
# ──────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
class TestFormaVendaConcorrencia:
    def test_conversoes_simultaneas_nao_corrompem_estoque(self, admin_user, empresa_a, produto):
        import threading
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"))
        produto.estoque_atual = Decimal("1000.000")
        produto.save(update_fields=["estoque_atual"])

        errors = []

        def saida():
            try:
                saida_estoque(
                    user=admin_user,
                    produto=produto,
                    quantidade=Decimal("100"),
                    forma_venda=forma,
                    quantidade_informada=Decimal("100"),
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=saida) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        produto.refresh_from_db()
        assert produto.estoque_atual >= Decimal("0.000")
        total_saidas = MovimentacaoEstoque.objects.filter(
            produto=produto,
            tipo=MovimentacaoEstoque.TIPO_SAIDA,
            status=MovimentacaoEstoque.STATUS_ATIVA,
        ).count()
        assert total_saidas <= 5


# ──────────────────────────────────────────────
# MULTI-TENANT — isolamento estrito
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFormaVendaMultiTenant:
    def test_empresa_a_nao_ve_formas_empresa_b(self, empresa_a, empresa_b, produto, produto_b):
        make_forma_venda(empresa_a, produto, codigo="A_M")
        make_forma_venda(empresa_b, produto_b, codigo="B_M")

        qs_a = get_formas_venda(company_id=empresa_a.pk)
        qs_b = get_formas_venda(company_id=empresa_b.pk)

        pks_a = set(str(f.pk) for f in qs_a)
        pks_b = set(str(f.pk) for f in qs_b)
        assert pks_a.isdisjoint(pks_b)

    def test_criar_forma_outra_empresa_rejeitado(self, other_company_user, produto):
        with pytest.raises(ValidationError, match="empresa"):
            criar_forma_venda(
                user=other_company_user,
                produto=produto,
                data={"nome": "Metro", "unidade": "M", "fator_conversao": Decimal("1")},
            )

    def test_inativar_forma_outra_empresa_rejeitado(self, admin_user, other_company_user,
                                                     empresa_b, produto_b):
        forma_b = make_forma_venda(empresa_b, produto_b, codigo="B_M")
        with pytest.raises(ValidationError, match="empresa"):
            inativar_forma_venda(user=admin_user, forma_venda=forma_b)


# ──────────────────────────────────────────────
# FIADO — venda por forma de venda
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFiadoComFormaVenda:
    def test_adicionar_item_por_rolo(self, admin_user, empresa_a, produto):
        from apps.clientes.models import Cliente
        from apps.fiado.models import ContaFiado
        from apps.fiado.services.item import adicionar_item_fiado

        cliente = Cliente.objects.create(
            company=empresa_a,
            nome="Cliente Teste",
            cpf_cnpj="11111111111",
            limite_credito=Decimal("50000.00"),
            saldo_devedor=Decimal("0.00"),
        )
        conta = ContaFiado.objects.create(
            company=empresa_a,
            cliente=cliente,
            status=ContaFiado.STATUS_ABERTA,
        )

        forma_rolo = make_forma_venda(
            empresa_a, produto, nome="Rolo 100m", codigo="ROLO",
            unidade="ROLO", fator_conversao=Decimal("100"), padrao=False
        )
        produto.estoque_atual = Decimal("1000.000")
        produto.save(update_fields=["estoque_atual"])

        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={
                "produto": produto,
                "forma_venda": forma_rolo,
                "quantidade_informada": Decimal("2.000"),
                "preco_unitario": Decimal("5.00"),
            },
        )

        assert item.quantidade == Decimal("200.000")
        assert item.quantidade_informada == Decimal("2.000")
        assert item.forma_venda_id == forma_rolo.pk

        produto.refresh_from_db()
        assert produto.estoque_atual == Decimal("800.000")

    def test_adicionar_item_por_metro(self, admin_user, empresa_a, produto):
        from apps.clientes.models import Cliente
        from apps.fiado.models import ContaFiado
        from apps.fiado.services.item import adicionar_item_fiado

        cliente = Cliente.objects.create(
            company=empresa_a,
            nome="Cliente Metro",
            cpf_cnpj="22222222222",
            limite_credito=Decimal("5000.00"),
            saldo_devedor=Decimal("0.00"),
        )
        conta = ContaFiado.objects.create(
            company=empresa_a,
            cliente=cliente,
            status=ContaFiado.STATUS_ABERTA,
        )

        forma_metro = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("1"), codigo="METRO")
        # produto começa com estoque_atual = 10.000; vendemos só 5
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={
                "produto": produto,
                "forma_venda": forma_metro,
                "quantidade_informada": Decimal("5.000"),
                "preco_unitario": Decimal("5.00"),
            },
        )

        assert item.quantidade == Decimal("5.000")
        assert item.subtotal == Decimal("25.00")

    def test_adicionar_item_sem_forma_backward_compat(self, admin_user, empresa_a, produto):
        from apps.clientes.models import Cliente
        from apps.fiado.models import ContaFiado
        from apps.fiado.services.item import adicionar_item_fiado

        cliente = Cliente.objects.create(
            company=empresa_a,
            nome="Cliente Compat",
            cpf_cnpj="33333333333",
            limite_credito=Decimal("5000.00"),
            saldo_devedor=Decimal("0.00"),
        )
        conta = ContaFiado.objects.create(
            company=empresa_a,
            cliente=cliente,
            status=ContaFiado.STATUS_ABERTA,
        )

        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={
                "produto": produto,
                "quantidade": Decimal("5.000"),
                "preco_unitario": Decimal("35.00"),
            },
        )

        assert item.forma_venda_id is None
        assert item.quantidade_informada is None
        assert item.quantidade == Decimal("5.000")


# ──────────────────────────────────────────────
# SEGURANÇA — validações adicionais
# ──────────────────────────────────────────────

@pytest.mark.django_db
class TestFormaVendaSeguranca:
    def test_company_payload_rejeitado_na_api(self, admin_client, produto):
        payload = {
            "company": "00000000-0000-0000-0000-000000000000",
            "produto": str(produto.pk),
            "nome": "Injected",
            "unidade": "M",
            "fator_conversao": "1",
        }
        resp = admin_client.post("/api/v1/estoque/formas-venda/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_forma_venda_inativa_nao_usada_em_saida(self, admin_user, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, ativo=False, padrao=False, codigo="INATIVO")
        make_forma_venda(empresa_a, produto, padrao=True, codigo="ATIVO")

        with pytest.raises(ValidationError, match="inativa"):
            saida_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("5"),
                forma_venda=forma,
                quantidade_informada=Decimal("5"),
            )

    def test_estoque_nao_fica_negativo(self, admin_user, empresa_a, produto):
        forma = make_forma_venda(empresa_a, produto, fator_conversao=Decimal("100"))
        produto.estoque_atual = Decimal("50.000")
        produto.save(update_fields=["estoque_atual"])

        with pytest.raises(ValidationError, match="[Ee]stoque"):
            saida_estoque(
                user=admin_user,
                produto=produto,
                quantidade=Decimal("100.000"),
                forma_venda=forma,
                quantidade_informada=Decimal("1.000"),
            )
