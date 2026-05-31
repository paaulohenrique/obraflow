from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.estoque.models import Produto
from apps.estoque.models import MovimentacaoEstoque
from apps.fiado.models import ContaFiado, HistoricoFiado, ItemFiado, PagamentoFiado
from apps.fiado.selectors import get_dashboard_fiado
from apps.fiado.services import (
    abrir_conta_fiado,
    adicionar_item_fiado,
    cancelar_conta_fiado,
    cancelar_item_fiado,
    cancelar_pagamento_fiado,
    registrar_pagamento_fiado,
    update_conta_fiado,
)
from .conftest import make_cliente, make_produto


@pytest.mark.django_db
class TestContaFiadoServices:
    def test_abrir_conta_cria_auditoria_e_historico(self, admin_user, cliente):
        conta = abrir_conta_fiado(
            user=admin_user,
            data={"cliente": cliente, "observacao": "Obra do centro"},
        )

        assert conta.company_id == admin_user.company_id
        assert conta.status == ContaFiado.STATUS_ABERTA
        assert conta.valor_restante == Decimal("0.00")
        assert AuditLog.objects.filter(entity_type="ContaFiado", entity_id=conta.pk).exists()
        assert HistoricoFiado.objects.filter(
            conta=conta,
            evento=HistoricoFiado.EVENTO_CONTA_CRIADA,
        ).exists()

    def test_impede_duas_contas_abertas_para_cliente(self, admin_user, cliente):
        abrir_conta_fiado(user=admin_user, data={"cliente": cliente})

        with pytest.raises(ValidationError, match="aberta"):
            abrir_conta_fiado(user=admin_user, data={"cliente": cliente})

    def test_impede_cliente_bloqueado_ou_inativo(
        self,
        admin_user,
        cliente_bloqueado,
        cliente_inativo,
    ):
        with pytest.raises(ValidationError, match="bloqueado"):
            abrir_conta_fiado(user=admin_user, data={"cliente": cliente_bloqueado})

        with pytest.raises(ValidationError, match="inativo"):
            abrir_conta_fiado(user=admin_user, data={"cliente": cliente_inativo})

    def test_update_conta_registra_historicos(self, admin_user, cliente):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        vencimento = timezone.localdate()

        conta = update_conta_fiado(
            user=admin_user,
            conta=conta,
            data={"data_vencimento": vencimento, "observacao": "Nova observação"},
        )

        assert conta.data_vencimento == vencimento
        assert HistoricoFiado.objects.filter(
            conta=conta,
            evento=HistoricoFiado.EVENTO_VENCIMENTO_ALTERADO,
        ).exists()
        assert HistoricoFiado.objects.filter(
            conta=conta,
            evento=HistoricoFiado.EVENTO_OBSERVACAO_ALTERADA,
        ).exists()

    def test_cancelar_conta_reverte_itens_sem_pagamento(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )

        conta = cancelar_conta_fiado(
            user=admin_user,
            conta=conta,
            motivo="Lançamento indevido",
        )

        item.refresh_from_db()
        produto.refresh_from_db()
        cliente.refresh_from_db()
        assert conta.status == ContaFiado.STATUS_CANCELADA
        assert item.status == ItemFiado.STATUS_CANCELADO
        assert produto.estoque_atual == Decimal("10.000")
        assert cliente.saldo_devedor == Decimal("0.00")

    def test_cancelar_conta_com_pagamento_falha(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()
        registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("10.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )

        with pytest.raises(ValidationError, match="pagamentos"):
            cancelar_conta_fiado(user=admin_user, conta=conta, motivo="Cancelar")


@pytest.mark.django_db
class TestItemFiadoServices:
    def test_adicionar_item_baixa_estoque_e_atualiza_saldos(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})

        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("3.000")},
        )

        produto.refresh_from_db()
        conta.refresh_from_db()
        cliente.refresh_from_db()

        assert item.subtotal == Decimal("150.00")
        assert item.movimentacao_estoque.tipo == MovimentacaoEstoque.TIPO_SAIDA
        assert item.movimentacao_estoque.idempotency_key == f"fiado_item:{item.pk}"
        assert produto.estoque_atual == Decimal("7.000")
        assert conta.valor_total == Decimal("150.00")
        assert conta.valor_restante == Decimal("150.00")
        assert cliente.saldo_devedor == Decimal("150.00")

    def test_estoque_insuficiente_aborta_sem_item(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})

        with pytest.raises(ValidationError, match="insuficiente"):
            adicionar_item_fiado(
                user=admin_user,
                conta=conta,
                data={"produto": produto, "quantidade": Decimal("99.000")},
            )

        produto.refresh_from_db()
        cliente.refresh_from_db()
        assert produto.estoque_atual == Decimal("10.000")
        assert cliente.saldo_devedor == Decimal("0.00")
        assert ItemFiado.objects.count() == 0

    def test_limite_credito_respeitado(self, admin_user, empresa_a):
        cliente = make_cliente(empresa_a, limite_credito=Decimal("40.00"))
        produto = make_produto(empresa_a, preco_venda=Decimal("50.00"))
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})

        with pytest.raises(ValidationError, match="Limite"):
            adicionar_item_fiado(
                user=admin_user,
                conta=conta,
                data={"produto": produto, "quantidade": Decimal("1.000")},
            )

    def test_item_idempotente(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        data = {
            "produto": produto,
            "quantidade": Decimal("1.000"),
            "idempotency_key": "pedido-caixa-1",
        }

        item_1 = adicionar_item_fiado(user=admin_user, conta=conta, data=data)
        item_2 = adicionar_item_fiado(user=admin_user, conta=conta, data=data)

        assert item_1.pk == item_2.pk
        assert ItemFiado.objects.count() == 1
        assert MovimentacaoEstoque.objects.count() == 1

    def test_cancelar_item_reverte_estoque_e_saldo(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )

        item = cancelar_item_fiado(user=admin_user, item=item, motivo="Cliente desistiu")

        produto.refresh_from_db()
        conta.refresh_from_db()
        cliente.refresh_from_db()
        assert item.status == ItemFiado.STATUS_CANCELADO
        assert item.movimentacao_cancelamento.tipo == MovimentacaoEstoque.TIPO_CANCELAMENTO
        assert produto.estoque_atual == Decimal("10.000")
        assert conta.valor_total == Decimal("0.00")
        assert cliente.saldo_devedor == Decimal("0.00")

        with pytest.raises(ValidationError, match="cancelado"):
            cancelar_item_fiado(user=admin_user, item=item, motivo="De novo")

    def test_cancelar_item_com_pagamento_excedente_falha(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()
        registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("10.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )

        with pytest.raises(ValidationError, match="pagamentos maiores"):
            cancelar_item_fiado(user=admin_user, item=item, motivo="Sem estorno na V1")

    def test_item_nao_edita_nem_deleta(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        item = adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )

        item.observacao = "mutação direta"
        with pytest.raises(RuntimeError):
            item.save()
        with pytest.raises(RuntimeError):
            item.delete()


@pytest.mark.django_db
class TestPagamentoFiadoServices:
    def test_pagamento_parcial_e_total_fecha_conta(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )
        conta.refresh_from_db()

        parcial = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("40.00"), "forma_pagamento": PagamentoFiado.FORMA_DINHEIRO},
        )
        conta.refresh_from_db()
        cliente.refresh_from_db()
        assert parcial.status == PagamentoFiado.STATUS_CONFIRMADO
        assert conta.status == ContaFiado.STATUS_ABERTA
        assert conta.valor_restante == Decimal("60.00")
        assert cliente.saldo_devedor == Decimal("60.00")
        assert cliente.data_ultimo_pagamento == timezone.localdate()

        registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("60.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )
        conta.refresh_from_db()
        cliente.refresh_from_db()
        assert conta.status == ContaFiado.STATUS_FECHADA
        assert conta.valor_restante == Decimal("0.00")
        assert cliente.saldo_devedor == Decimal("0.00")

    def test_pagamento_maior_que_restante_falha(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()

        with pytest.raises(ValidationError, match="maior"):
            registrar_pagamento_fiado(
                user=admin_user,
                conta=conta,
                data={"valor": Decimal("99.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
            )

    def test_pagamento_idempotente(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )
        conta.refresh_from_db()
        data = {
            "valor": Decimal("20.00"),
            "forma_pagamento": PagamentoFiado.FORMA_PIX,
            "idempotency_key": "pix-123",
        }

        p1 = registrar_pagamento_fiado(user=admin_user, conta=conta, data=data)
        p2 = registrar_pagamento_fiado(user=admin_user, conta=conta, data=data)

        conta.refresh_from_db()
        assert p1.pk == p2.pk
        assert PagamentoFiado.objects.count() == 1
        assert conta.valor_pago == Decimal("20.00")

    def test_cancelar_pagamento_reabre_conta(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()
        pagamento = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("50.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )
        conta.refresh_from_db()
        assert conta.status == ContaFiado.STATUS_FECHADA

        pagamento = cancelar_pagamento_fiado(
            user=admin_user,
            pagamento=pagamento,
            motivo="PIX estornado",
        )

        conta.refresh_from_db()
        cliente.refresh_from_db()
        assert pagamento.status == PagamentoFiado.STATUS_CANCELADO
        assert conta.status == ContaFiado.STATUS_ABERTA
        assert conta.valor_restante == Decimal("50.00")
        assert cliente.saldo_devedor == Decimal("50.00")
        assert cliente.data_ultimo_pagamento is None

        with pytest.raises(ValidationError, match="cancelado"):
            cancelar_pagamento_fiado(user=admin_user, pagamento=pagamento, motivo="De novo")

    def test_conta_fechada_ou_cancelada_nao_recebe_item_nem_pagamento(
        self,
        admin_user,
        cliente,
        produto,
    ):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()
        registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("50.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )
        conta.refresh_from_db()

        with pytest.raises(ValidationError, match="aberta"):
            adicionar_item_fiado(
                user=admin_user,
                conta=conta,
                data={"produto": produto, "quantidade": Decimal("1.000")},
            )

        cliente2 = make_cliente(admin_user.company, nome="Cliente 2")
        produto2 = make_produto(admin_user.company)
        conta2 = abrir_conta_fiado(user=admin_user, data={"cliente": cliente2})
        cancelar_conta_fiado(user=admin_user, conta=conta2, motivo="Sem compra")
        conta2.refresh_from_db()
        with pytest.raises(ValidationError, match="aberta"):
            registrar_pagamento_fiado(
                user=admin_user,
                conta=conta2,
                data={"valor": Decimal("1.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
            )
        with pytest.raises(ValidationError, match="aberta"):
            adicionar_item_fiado(
                user=admin_user,
                conta=conta2,
                data={"produto": produto2, "quantidade": Decimal("1.000")},
            )

    def test_pagamento_nao_edita_nem_deleta(self, admin_user, cliente, produto):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()
        pagamento = registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("10.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )

        pagamento.observacao = "mutação direta"
        with pytest.raises(RuntimeError):
            pagamento.save()
        with pytest.raises(RuntimeError):
            pagamento.delete()


@pytest.mark.django_db
class TestSelectorsDashboard:
    def test_dashboard_e_tenant_isolation(self, admin_user, other_company_user, cliente, produto):
        conta = abrir_conta_fiado(
            user=admin_user,
            data={
                "cliente": cliente,
                "data_vencimento": timezone.localdate() - timezone.timedelta(days=2),
            },
        )
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("2.000")},
        )
        conta.refresh_from_db()
        registrar_pagamento_fiado(
            user=admin_user,
            conta=conta,
            data={"valor": Decimal("25.00"), "forma_pagamento": PagamentoFiado.FORMA_PIX},
        )

        outro_cliente = make_cliente(other_company_user.company, nome="Outro tenant")
        outro_produto = make_produto(other_company_user.company, preco_venda=Decimal("500.00"))
        outra_conta = abrir_conta_fiado(user=other_company_user, data={"cliente": outro_cliente})
        adicionar_item_fiado(
            user=other_company_user,
            conta=outra_conta,
            data={"produto": outro_produto, "quantidade": Decimal("1.000")},
        )

        data = get_dashboard_fiado(company_id=admin_user.company_id)

        assert data["total_em_aberto"] == Decimal("75.00")
        assert data["total_atrasado"] == Decimal("75.00")
        assert data["total_recebido_hoje"] == Decimal("25.00")
        assert data["contas_abertas"] == 1
        assert data["clientes_devedores"] == 1

    def test_historico_nao_edita_nem_deleta(self, admin_user, cliente):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        historico = HistoricoFiado.objects.get(conta=conta)

        historico.descricao = "mutação direta"
        with pytest.raises(RuntimeError):
            historico.save()
        with pytest.raises(RuntimeError):
            historico.delete()


@pytest.mark.django_db(transaction=True)
class TestFiadoConcurrency:
    def test_duas_compras_simultaneas_nao_ultrapassam_limite(self, admin_user, empresa_a):
        cliente = make_cliente(empresa_a, limite_credito=Decimal("50.00"))
        produto = make_produto(empresa_a, preco_venda=Decimal("50.00"), estoque_atual=Decimal("10.000"))
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})

        def worker(key):
            close_old_connections()
            user = User.objects.get(pk=admin_user.pk)
            conta_thread = ContaFiado.objects.get(pk=conta.pk)
            produto_thread = Produto.objects.get(pk=produto.pk)
            try:
                adicionar_item_fiado(
                    user=user,
                    conta=conta_thread,
                    data={
                        "produto": produto_thread,
                        "quantidade": Decimal("1.000"),
                        "idempotency_key": key,
                    },
                )
                return "ok"
            except ValidationError:
                return "fail"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(worker, ["compra-1", "compra-2"]))

        conta.refresh_from_db()
        cliente.refresh_from_db()
        produto.refresh_from_db()

        assert results.count("ok") == 1
        assert ItemFiado.objects.filter(status=ItemFiado.STATUS_ATIVO).count() == 1
        assert conta.valor_restante == Decimal("50.00")
        assert cliente.saldo_devedor == Decimal("50.00")
        assert produto.estoque_atual == Decimal("9.000")

    def test_dois_pagamentos_simultaneos_nao_deixam_restante_negativo(
        self,
        admin_user,
        cliente,
        produto,
    ):
        conta = abrir_conta_fiado(user=admin_user, data={"cliente": cliente})
        adicionar_item_fiado(
            user=admin_user,
            conta=conta,
            data={"produto": produto, "quantidade": Decimal("1.000")},
        )
        conta.refresh_from_db()

        def worker(key):
            close_old_connections()
            user = User.objects.get(pk=admin_user.pk)
            conta_thread = ContaFiado.objects.get(pk=conta.pk)
            try:
                registrar_pagamento_fiado(
                    user=user,
                    conta=conta_thread,
                    data={
                        "valor": Decimal("50.00"),
                        "forma_pagamento": PagamentoFiado.FORMA_PIX,
                        "idempotency_key": key,
                    },
                )
                return "ok"
            except ValidationError:
                return "fail"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(worker, ["pix-1", "pix-2"]))

        conta.refresh_from_db()
        cliente.refresh_from_db()

        assert results.count("ok") == 1
        assert PagamentoFiado.objects.filter(status=PagamentoFiado.STATUS_CONFIRMADO).count() == 1
        assert conta.valor_pago == Decimal("50.00")
        assert conta.valor_restante == Decimal("0.00")
        assert conta.status == ContaFiado.STATUS_FECHADA
        assert cliente.saldo_devedor == Decimal("0.00")
