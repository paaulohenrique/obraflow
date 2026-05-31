from decimal import Decimal
from threading import Barrier, Thread

import pytest
from django.db import connections

from apps.estoque.models import Produto
from apps.estoque.services import entrada_estoque, saida_estoque


def run_concurrently(*calls):
    barrier = Barrier(len(calls))
    results = []

    def worker(fn):
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            results.append(("ok", fn()))
        except Exception as exc:  # noqa: BLE001 - tests assert expected concurrent failures
            results.append(("error", exc))
        finally:
            connections.close_all()

    threads = [Thread(target=worker, args=(fn,)) for fn in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return results


@pytest.mark.django_db(transaction=True)
def test_duas_saidas_simultaneas_nao_deixam_estoque_negativo(admin_user, produto):
    produto.estoque_atual = Decimal("5.000")
    produto.save(update_fields=["estoque_atual", "updated_at"])

    results = run_concurrently(
        lambda: saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("4.000"),
        ),
        lambda: saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("4.000"),
        ),
    )
    produto_final = Produto.objects.get(pk=produto.pk)

    assert [status for status, _ in results].count("ok") == 1
    assert [status for status, _ in results].count("error") == 1
    assert produto_final.estoque_atual == Decimal("1.000")


@pytest.mark.django_db(transaction=True)
def test_entrada_e_saida_simultaneas_mantem_saldo_consistente(admin_user, produto):
    produto.estoque_atual = Decimal("10.000")
    produto.save(update_fields=["estoque_atual", "updated_at"])

    results = run_concurrently(
        lambda: entrada_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("5.000"),
        ),
        lambda: saida_estoque(
            user=admin_user,
            produto=produto,
            quantidade=Decimal("7.000"),
        ),
    )
    produto_final = Produto.objects.get(pk=produto.pk)

    assert [status for status, _ in results].count("ok") == 2
    assert produto_final.estoque_atual == Decimal("8.000")
