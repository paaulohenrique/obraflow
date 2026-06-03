from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.fiado.models import PagamentoFiado
from apps.fiado.services import abrir_conta_fiado, adicionar_item_fiado, cancelar_pagamento_fiado, registrar_pagamento_fiado
from apps.financeiro.models import (
    CaixaDiario,
    CategoriaFinanceira,
    ConfiguracaoFinanceiraOperacional,
    ContaFinanceira,
    ContaPagar,
    LancamentoFinanceiro,
)
from apps.financeiro.services import (
    abrir_caixa,
    ajustar_saldo_conta,
    atualizar_configuracao_financeira_operacional,
    cancelar_conta_pagar,
    cancelar_lancamento_financeiro,
    criar_categoria_financeira,
    criar_categorias_padrao_empresa,
    criar_conta_financeira,
    criar_conta_pagar,
    criar_lancamento_financeiro,
    fechar_caixa,
    get_or_create_configuracao_financeira_operacional,
    inativar_categoria_financeira,
    inativar_conta_financeira,
    pagar_conta_pagar,
    reabrir_caixa,
    resolver_conta_operacional_pdv,
)
from apps.financeiro.services.integracao_fiado import registrar_recebimento_fiado
from .conftest import make_categoria_financeira, make_conta_financeira, make_fornecedor


@pytest.mark.django_db
class TestContaFinanceiraServices:
    def test_criar_conta_e_ajustar_saldo_gera_lancamento(self, admin_user, receita):
        conta = criar_conta_financeira(
            user=admin_user,
            data={"nome": "Banco novo", "tipo": ContaFinanceira.TIPO_BANCO},
        )

        lancamento = ajustar_saldo_conta(
            user=admin_user,
            conta=conta,
            data={
                "tipo": LancamentoFinanceiro.TIPO_ENTRADA,
                "valor": Decimal("100.00"),
                "categoria": receita,
                "descricao": "Saldo inicial",
            },
        )

        conta.refresh_from_db()
        assert conta.saldo_atual == Decimal("100.00")
        assert lancamento.origem_tipo == LancamentoFinanceiro.ORIGEM_AJUSTE
        assert AuditLog.objects.filter(entity_type="ContaFinanceira", entity_id=conta.pk).exists()

    def test_saldo_nao_altera_direto_e_nao_fica_negativo(self, admin_user, banco, despesa):
        banco.saldo_atual = Decimal("10.00")
        with pytest.raises(RuntimeError):
            banco.save()

        with pytest.raises(ValidationError, match="negativa"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=banco,
                categoria=despesa,
                tipo=LancamentoFinanceiro.TIPO_SAIDA,
                valor=Decimal("1.00"),
            )

    def test_inativar_conta_respeita_saldo_e_lancamentos(self, admin_user, empresa_a, receita):
        vazia = criar_conta_financeira(
            user=admin_user,
            data={"nome": "Carteira vazia", "tipo": ContaFinanceira.TIPO_CARTEIRA},
        )
        inativar_conta_financeira(user=admin_user, conta=vazia)
        vazia.refresh_from_db()
        assert vazia.ativo is False

        com_saldo = criar_conta_financeira(
            user=admin_user,
            data={"nome": "Banco saldo", "tipo": ContaFinanceira.TIPO_BANCO},
        )
        ajustar_saldo_conta(
            user=admin_user,
            conta=com_saldo,
            data={"tipo": LancamentoFinanceiro.TIPO_ENTRADA, "valor": Decimal("5.00"), "categoria": receita},
        )
        with pytest.raises(ValidationError, match="saldo"):
            inativar_conta_financeira(user=admin_user, conta=com_saldo)

    def test_configuracao_operacional_resolve_conta_do_pdv(self, admin_user, empresa_a):
        conta_pix = criar_conta_financeira(
            user=admin_user,
            data={"nome": "Conta PIX Principal", "tipo": ContaFinanceira.TIPO_BANCO},
        )
        caixa = criar_conta_financeira(
            user=admin_user,
            data={"nome": "Caixa Principal", "tipo": ContaFinanceira.TIPO_CAIXA},
        )
        config = get_or_create_configuracao_financeira_operacional(company_id=empresa_a.pk)

        atualizar_configuracao_financeira_operacional(
            user=admin_user,
            config=config,
            data={"conta_pix": conta_pix, "conta_dinheiro": caixa},
        )

        config.refresh_from_db()
        assert ConfiguracaoFinanceiraOperacional.objects.filter(company=empresa_a).count() == 1
        assert resolver_conta_operacional_pdv(
            company_id=empresa_a.pk,
            forma_pagamento=LancamentoFinanceiro.FORMA_PIX,
        ) == conta_pix
        assert resolver_conta_operacional_pdv(
            company_id=empresa_a.pk,
            forma_pagamento=LancamentoFinanceiro.FORMA_DINHEIRO,
        ) == caixa


@pytest.mark.django_db
class TestCategoriaFinanceiraServices:
    def test_criar_categoria_e_padroes(self, admin_user, empresa_a):
        categoria = criar_categoria_financeira(
            user=admin_user,
            data={"nome": "Serviços", "tipo": CategoriaFinanceira.TIPO_RECEITA},
        )
        padroes = criar_categorias_padrao_empresa(empresa_a)

        assert categoria.tipo == CategoriaFinanceira.TIPO_RECEITA
        assert CategoriaFinanceira.objects.filter(nome="Fiado", company=empresa_a).exists()
        assert len(padroes) >= 10

    def test_categoria_incompativel_com_tipo_falha(self, admin_user, banco, receita, despesa):
        with pytest.raises(ValidationError, match="Saída exige"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=banco,
                categoria=receita,
                tipo=LancamentoFinanceiro.TIPO_SAIDA,
                valor=Decimal("1.00"),
            )

        with pytest.raises(ValidationError, match="Entrada exige"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=banco,
                categoria=despesa,
                tipo=LancamentoFinanceiro.TIPO_ENTRADA,
                valor=Decimal("1.00"),
            )

    def test_inativar_categoria_com_lancamento_falha(self, admin_user, banco, receita):
        criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=banco,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("20.00"),
        )
        with pytest.raises(ValidationError, match="lançamentos"):
            inativar_categoria_financeira(user=admin_user, categoria=receita)

    def test_inativar_categoria_sem_lancamento(self, admin_user, empresa_a):
        categoria = criar_categoria_financeira(
            user=admin_user,
            data={"nome": "Taxa avulsa", "tipo": CategoriaFinanceira.TIPO_DESPESA},
        )
        categoria = inativar_categoria_financeira(user=admin_user, categoria=categoria)
        assert categoria.ativa is False


@pytest.mark.django_db
class TestLancamentoFinanceiroServices:
    def test_entrada_saida_idempotencia_e_cancelamento(self, admin_user, banco, receita, despesa):
        entrada = criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=banco,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("100.00"),
            idempotency_key="entrada-1",
        )
        mesma = criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=banco,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("100.00"),
            idempotency_key="entrada-1",
        )
        saida = criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=banco,
            categoria=despesa,
            tipo=LancamentoFinanceiro.TIPO_SAIDA,
            valor=Decimal("40.00"),
        )
        criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=banco,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("100.00"),
        )
        estorno = cancelar_lancamento_financeiro(
            user=admin_user,
            lancamento=entrada,
            motivo="Duplicado",
            idempotency_key="cancelar-entrada-1",
        )
        mesmo_estorno = cancelar_lancamento_financeiro(
            user=admin_user,
            lancamento=entrada,
            motivo="Duplicado",
            idempotency_key="cancelar-entrada-1",
        )

        banco.refresh_from_db()
        entrada.refresh_from_db()
        assert mesma.pk == entrada.pk
        assert mesmo_estorno.pk == estorno.pk
        assert saida.valor == Decimal("40.00")
        assert estorno.tipo == LancamentoFinanceiro.TIPO_SAIDA
        assert estorno.estorno_de_id == entrada.pk
        assert entrada.status == LancamentoFinanceiro.STATUS_CANCELADO
        assert banco.saldo_atual == Decimal("60.00")

        with pytest.raises(ValidationError, match="cancelado"):
            cancelar_lancamento_financeiro(user=admin_user, lancamento=entrada, motivo="De novo")

    def test_lancamento_nao_edita_nem_deleta(self, admin_user, banco, receita):
        lancamento = criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=banco,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("10.00"),
        )
        lancamento.descricao = "mutação direta"
        with pytest.raises(RuntimeError):
            lancamento.save()
        with pytest.raises(RuntimeError):
            lancamento.delete()

    def test_validacoes_de_conta_categoria_caixa_e_estorno(
        self,
        admin_user,
        banco,
        caixa,
        receita,
        despesa,
        empresa_a,
    ):
        categoria_inativa = make_categoria_financeira(
            empresa_a,
            nome="Receita inativa",
            tipo=CategoriaFinanceira.TIPO_RECEITA,
        )
        categoria_inativa.ativa = False
        categoria_inativa.save(update_fields=["ativa"])
        with pytest.raises(ValidationError, match="Categoria financeira inativa"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=banco,
                categoria=categoria_inativa,
                tipo=LancamentoFinanceiro.TIPO_ENTRADA,
                valor=Decimal("1.00"),
            )

        banco.ativo = False
        banco.save(update_fields=["ativo"])
        with pytest.raises(ValidationError, match="Conta financeira inativa"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=banco,
                categoria=receita,
                tipo=LancamentoFinanceiro.TIPO_ENTRADA,
                valor=Decimal("1.00"),
            )
        banco.ativo = True
        banco.save(update_fields=["ativo"])

        with pytest.raises(ValidationError, match="dinheiro exige"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=banco,
                categoria=receita,
                tipo=LancamentoFinanceiro.TIPO_ENTRADA,
                valor=Decimal("1.00"),
                forma_pagamento=LancamentoFinanceiro.FORMA_DINHEIRO,
            )

        caixa_diario = abrir_caixa(user=admin_user, data={"conta_financeira": caixa})
        with pytest.raises(ValidationError, match="não pertence"):
            criar_lancamento_financeiro(
                user=admin_user,
                conta_financeira=caixa,
                categoria=receita,
                tipo=LancamentoFinanceiro.TIPO_ENTRADA,
                valor=Decimal("1.00"),
                caixa_diario=CaixaDiario.objects.create(
                    company=empresa_a,
                    conta_financeira=make_conta_financeira(
                        empresa_a,
                        nome="Outro caixa",
                        tipo=ContaFinanceira.TIPO_CAIXA,
                    ),
                    data=timezone.localdate() + timedelta(days=1),
                ),
            )

        lancamento = criar_lancamento_financeiro(
            user=admin_user,
            conta_financeira=caixa,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("5.00"),
            forma_pagamento=LancamentoFinanceiro.FORMA_DINHEIRO,
        )
        estorno = cancelar_lancamento_financeiro(
            user=admin_user,
            lancamento=lancamento,
            motivo="Cancelar",
        )
        with pytest.raises(ValidationError, match="estorno"):
            cancelar_lancamento_financeiro(user=admin_user, lancamento=estorno, motivo="Cancelar")
        caixa_diario.refresh_from_db()
        assert caixa_diario.total_entradas == Decimal("5.00")
        assert caixa_diario.total_saidas == Decimal("5.00")


@pytest.mark.django_db
class TestContaPagarServices:
    def test_pagamento_parcial_total_e_lancamento_saida(
        self,
        admin_user,
        banco_com_saldo,
        despesa,
        fornecedor,
    ):
        conta = criar_conta_pagar(
            user=admin_user,
            data={
                "fornecedor": fornecedor,
                "descricao": "Fornecedor",
                "categoria": despesa,
                "valor_total": Decimal("100.00"),
                "data_vencimento": timezone.localdate(),
            },
        )

        pagar_conta_pagar(
            user=admin_user,
            conta=conta,
            data={
                "conta_financeira": banco_com_saldo,
                "valor": Decimal("40.00"),
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
                "idempotency_key": "pagamento-fornecedor-1",
            },
        )
        conta.refresh_from_db()
        assert conta.is_parcial is True
        assert conta.valor_restante == Decimal("60.00")

        pagar_conta_pagar(
            user=admin_user,
            conta=conta,
            data={
                "conta_financeira": banco_com_saldo,
                "valor": Decimal("60.00"),
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
            },
        )
        conta.refresh_from_db()
        banco_com_saldo.refresh_from_db()
        assert conta.status == ContaPagar.STATUS_PAGA
        assert banco_com_saldo.saldo_atual == Decimal("400.00")
        assert LancamentoFinanceiro.objects.filter(
            origem_tipo=LancamentoFinanceiro.ORIGEM_CONTA_PAGAR,
            origem_id=conta.pk,
            tipo=LancamentoFinanceiro.TIPO_SAIDA,
        ).count() == 2

    def test_pagamento_maior_e_cancelamentos(self, admin_user, banco_com_saldo, despesa):
        conta = criar_conta_pagar(
            user=admin_user,
            data={
                "descricao": "Aluguel",
                "categoria": despesa,
                "valor_total": Decimal("50.00"),
                "data_vencimento": timezone.localdate(),
            },
        )
        with pytest.raises(ValidationError, match="maior"):
            pagar_conta_pagar(
                user=admin_user,
                conta=conta,
                data={
                    "conta_financeira": banco_com_saldo,
                    "valor": Decimal("60.00"),
                    "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
                },
            )

        cancelada = criar_conta_pagar(
            user=admin_user,
            data={
                "descricao": "Internet",
                "categoria": despesa,
                "valor_total": Decimal("30.00"),
                "data_vencimento": timezone.localdate(),
            },
        )
        cancelada = cancelar_conta_pagar(user=admin_user, conta=cancelada, motivo="Duplicada")
        assert cancelada.status == ContaPagar.STATUS_CANCELADA

        pagar_conta_pagar(
            user=admin_user,
            conta=conta,
            data={
                "conta_financeira": banco_com_saldo,
                "valor": Decimal("10.00"),
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
            },
        )
        with pytest.raises(ValidationError, match="pagamento"):
            cancelar_conta_pagar(user=admin_user, conta=conta, motivo="Tentar")

    def test_update_conta_pagar_e_idempotencia(self, admin_user, banco_com_saldo, despesa, empresa_a):
        fornecedor = make_fornecedor(
            empresa_a,
            razao_social="Fornecedor Update",
            cnpj="11222333000181",
        )
        outra_despesa = make_categoria_financeira(
            empresa_a,
            nome="Manutenção",
            tipo=CategoriaFinanceira.TIPO_DESPESA,
        )
        receita = make_categoria_financeira(
            empresa_a,
            nome="Receita indevida",
            tipo=CategoriaFinanceira.TIPO_RECEITA,
        )
        conta = criar_conta_pagar(
            user=admin_user,
            data={
                "descricao": "Original",
                "categoria": despesa,
                "valor_total": Decimal("20.00"),
                "data_vencimento": timezone.localdate(),
            },
        )

        from apps.financeiro.services.conta_pagar import update_conta_pagar

        conta = update_conta_pagar(
            user=admin_user,
            conta=conta,
            data={
                "fornecedor": fornecedor,
                "categoria": outra_despesa,
                "descricao": "Atualizada",
                "valor_total": Decimal("30.00"),
                "observacao": "Ok",
            },
        )
        assert conta.descricao == "Atualizada"
        assert conta.valor_restante == Decimal("30.00")

        with pytest.raises(ValidationError, match="despesa"):
            update_conta_pagar(user=admin_user, conta=conta, data={"categoria": receita})

        pagar_conta_pagar(
            user=admin_user,
            conta=conta,
            data={
                "conta_financeira": banco_com_saldo,
                "valor": Decimal("10.00"),
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
                "idempotency_key": "conta-pagar-idempotente",
            },
        )
        conta = pagar_conta_pagar(
            user=admin_user,
            conta=conta,
            data={
                "conta_financeira": banco_com_saldo,
                "valor": Decimal("10.00"),
                "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
                "idempotency_key": "conta-pagar-idempotente",
            },
        )
        conta.refresh_from_db()
        assert conta.valor_pago == Decimal("10.00")
        with pytest.raises(ValidationError, match="sem pagamento"):
            update_conta_pagar(user=admin_user, conta=conta, data={"descricao": "Depois"})


@pytest.mark.django_db
class TestCaixaDiarioServices:
    def test_abrir_fechar_reabrir_e_lancamento_dinheiro(self, admin_user, manager_user, caixa, receita, despesa):
        caixa_diario = abrir_caixa(user=manager_user, data={"conta_financeira": caixa})
        with pytest.raises(ValidationError, match="aberto"):
            abrir_caixa(user=manager_user, data={"conta_financeira": caixa})

        entrada = criar_lancamento_financeiro(
            user=manager_user,
            conta_financeira=caixa,
            categoria=receita,
            tipo=LancamentoFinanceiro.TIPO_ENTRADA,
            valor=Decimal("100.00"),
            forma_pagamento=LancamentoFinanceiro.FORMA_DINHEIRO,
        )
        criar_lancamento_financeiro(
            user=manager_user,
            conta_financeira=caixa,
            categoria=despesa,
            tipo=LancamentoFinanceiro.TIPO_SAIDA,
            valor=Decimal("20.00"),
            forma_pagamento=LancamentoFinanceiro.FORMA_DINHEIRO,
        )
        caixa_diario.refresh_from_db()
        assert entrada.caixa_diario_id == caixa_diario.pk
        assert caixa_diario.total_entradas == Decimal("100.00")
        assert caixa_diario.total_saidas == Decimal("20.00")

        caixa_diario = fechar_caixa(user=manager_user, caixa=caixa_diario)
        assert caixa_diario.status == CaixaDiario.STATUS_FECHADO
        with pytest.raises(ValidationError, match="caixa aberto"):
            criar_lancamento_financeiro(
                user=manager_user,
                conta_financeira=caixa,
                categoria=receita,
                tipo=LancamentoFinanceiro.TIPO_ENTRADA,
                valor=Decimal("1.00"),
                forma_pagamento=LancamentoFinanceiro.FORMA_DINHEIRO,
            )
        with pytest.raises(Exception):
            reabrir_caixa(user=manager_user, caixa=caixa_diario)
        reaberto = reabrir_caixa(user=admin_user, caixa=caixa_diario)
        assert reaberto.status == CaixaDiario.STATUS_ABERTO

    def test_validacoes_caixa(self, admin_user, banco, caixa):
        with pytest.raises(ValidationError, match="tipo CAIXA"):
            abrir_caixa(user=admin_user, data={"conta_financeira": banco})

        caixa.ativo = False
        caixa.save(update_fields=["ativo"])
        with pytest.raises(ValidationError, match="inativa"):
            abrir_caixa(user=admin_user, data={"conta_financeira": caixa})
        caixa.ativo = True
        caixa.save(update_fields=["ativo"])

        caixa_diario = abrir_caixa(user=admin_user, data={"conta_financeira": caixa})
        with pytest.raises(ValidationError, match="aberto"):
            reabrir_caixa(user=admin_user, caixa=caixa_diario)
        fechado = fechar_caixa(user=admin_user, caixa=caixa_diario)
        with pytest.raises(ValidationError, match="aberto"):
            fechar_caixa(user=admin_user, caixa=fechado)


@pytest.mark.django_db(transaction=True)
class TestConcorrenciaFinanceiro:
    def test_dois_pagamentos_da_mesma_conta_nao_passam_do_restante(
        self,
        admin_user,
        banco_com_saldo,
        despesa,
    ):
        conta = criar_conta_pagar(
            user=admin_user,
            data={
                "descricao": "Concorrência",
                "categoria": despesa,
                "valor_total": Decimal("100.00"),
                "data_vencimento": timezone.localdate(),
            },
        )

        def pagar(valor, key):
            close_old_connections()
            try:
                return pagar_conta_pagar(
                    user=admin_user,
                    conta=conta,
                    data={
                        "conta_financeira": banco_com_saldo,
                        "valor": valor,
                        "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
                        "idempotency_key": key,
                    },
                ).valor_pago
            except Exception as exc:
                return str(exc)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda args: pagar(*args), [(Decimal("80.00"), "p1"), (Decimal("80.00"), "p2")]))

        conta.refresh_from_db()
        assert conta.valor_pago <= Decimal("100.00")
        assert any("maior" in str(result) for result in results)


@pytest.mark.django_db
class TestIntegracaoFiadoFinanceiro:
    def test_pagamento_fiado_cria_lancamento_e_cancelamento_estorna(
        self,
        admin_user,
        banco,
        cliente,
        produto,
    ):
        conta_fiado = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta_fiado,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta_fiado.refresh_from_db()

        pagamento = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta_fiado,
            data={
                "valor": Decimal("20.00"),
                "forma_pagamento": PagamentoFiado.FORMA_PIX,
                "conta_financeira": banco,
                "idempotency_key": "fiado-pix-1",
            },
        )

        lancamento = LancamentoFinanceiro.objects.get(
            origem_tipo=LancamentoFinanceiro.ORIGEM_FIADO,
            origem_id=pagamento.pk,
        )
        banco.refresh_from_db()
        assert lancamento.tipo == LancamentoFinanceiro.TIPO_ENTRADA
        assert lancamento.valor == Decimal("20.00")
        assert banco.saldo_atual == Decimal("20.00")

        cancelar_pagamento_fiado(user=admin_user, pagamento=pagamento, motivo="PIX estornado")
        lancamento.refresh_from_db()
        banco.refresh_from_db()
        assert lancamento.status == LancamentoFinanceiro.STATUS_CANCELADO
        assert LancamentoFinanceiro.objects.filter(estorno_de=lancamento).exists()
        assert banco.saldo_atual == Decimal("0.00")

    def test_pix_usa_conta_padrao_e_dinheiro_exige_caixa_aberto(
        self,
        admin_user,
        banco,
        caixa,
        cliente,
        produto,
    ):
        conta_fiado = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta_fiado,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )
        conta_fiado.refresh_from_db()

        pix = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta_fiado,
            data={"valor": Decimal("10.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )
        assert LancamentoFinanceiro.objects.get(origem_id=pix.pk).conta_financeira_id == banco.pk

        with pytest.raises(ValidationError, match="caixa aberto"):
            registrar_pagamento_fiado(
                user=admin_user,
                conta=conta_fiado,
                data={
                    "valor": Decimal("10.00"),
                    "forma_pagamento": PagamentoFiado.FORMA_DINHEIRO,
                    "conta_financeira": caixa,
                },
            )

        abrir_caixa(user=admin_user, data={"conta_financeira": caixa})
        dinheiro = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta_fiado,
            data={
                "valor": Decimal("10.00"),
                "forma_pagamento": PagamentoFiado.FORMA_DINHEIRO,
                "conta_financeira": caixa,
            },
        )
        assert LancamentoFinanceiro.objects.get(origem_id=dinheiro.pk).caixa_diario is not None

    def test_integracao_fiado_sem_conta_padrao_ou_usuario_falha(self, admin_user, cliente, produto):
        conta_fiado = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta_fiado,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta_fiado.refresh_from_db()
        pagamento = PagamentoFiado.objects.create(
            company=admin_user.company,
            conta=conta_fiado,
            valor=Decimal("1.00"),
            forma_pagamento=PagamentoFiado.FORMA_PIX,
        )
        with pytest.raises(ValidationError, match="Usuário"):
            registrar_recebimento_fiado(pagamento)
        with pytest.raises(ValidationError, match="Conta financeira padrão"):
            registrar_recebimento_fiado(pagamento, user=admin_user)
