from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.financeiro.filters import CaixaDiarioFilter, ContaPagarFilter, LancamentoFinanceiroFilter
from apps.financeiro.models import CaixaDiario, ContaPagar, LancamentoFinanceiro
from apps.financeiro.selectors import (
    get_caixa_by_id,
    get_categoria_by_id,
    get_conta_financeira_by_id,
    get_conta_pagar_by_id,
    get_contas_financeiras,
    get_lancamento_by_id,
    search_caixas,
    search_contas_pagar,
    search_lancamentos,
)
from apps.financeiro.services import abrir_caixa, criar_conta_pagar, criar_lancamento_financeiro, pagar_conta_pagar


@pytest.mark.django_db
def test_get_by_id_selectors_and_permission_denied(admin_user, banco, receita, despesa):
    lancamento = criar_lancamento_financeiro(
        user=admin_user,
        conta_financeira=banco,
        categoria=receita,
        tipo=LancamentoFinanceiro.TIPO_ENTRADA,
        valor=Decimal("100.00"),
    )
    conta_pagar = criar_conta_pagar(
        user=admin_user,
        data={
            "descricao": "Filtro",
            "categoria": despesa,
            "valor_total": Decimal("10.00"),
            "data_vencimento": timezone.localdate(),
        },
    )

    assert get_conta_financeira_by_id(company_id=admin_user.company_id, conta_id=banco.pk) == banco
    assert get_categoria_by_id(company_id=admin_user.company_id, categoria_id=receita.pk) == receita
    assert get_lancamento_by_id(company_id=admin_user.company_id, lancamento_id=lancamento.pk) == lancamento
    assert get_conta_pagar_by_id(company_id=admin_user.company_id, conta_id=conta_pagar.pk) == conta_pagar
    with pytest.raises(PermissionDenied):
        get_contas_financeiras(company_id=None).count()
    with pytest.raises(NotFound):
        get_caixa_by_id(company_id=admin_user.company_id, caixa_id="malformado")


@pytest.mark.django_db
def test_search_lancamentos_and_filterset(admin_user, banco, banco_com_saldo, receita, despesa):
    entrada = criar_lancamento_financeiro(
        user=admin_user,
        conta_financeira=banco,
        categoria=receita,
        tipo=LancamentoFinanceiro.TIPO_ENTRADA,
        valor=Decimal("70.00"),
        descricao="Receita especial",
        forma_pagamento=LancamentoFinanceiro.FORMA_PIX,
        idempotency_key="busca-entrada",
    )
    criar_lancamento_financeiro(
        user=admin_user,
        conta_financeira=banco_com_saldo,
        categoria=despesa,
        tipo=LancamentoFinanceiro.TIPO_SAIDA,
        valor=Decimal("30.00"),
        descricao="Despesa especial",
        forma_pagamento=LancamentoFinanceiro.FORMA_TRANSFERENCIA,
    )

    filters = {
        "conta_financeira": str(banco.pk),
        "categoria": str(receita.pk),
        "tipo": LancamentoFinanceiro.TIPO_ENTRADA,
        "status": LancamentoFinanceiro.STATUS_CONFIRMADO,
        "origem_tipo": LancamentoFinanceiro.ORIGEM_MANUAL,
        "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
        "data_lancamento_after": str(timezone.localdate()),
        "data_lancamento_before": str(timezone.localdate()),
        "valor_gte": "10",
        "valor_lte": "80",
        "search": "busca-entrada",
    }
    assert list(search_lancamentos(company_id=admin_user.company_id, filters=filters)) == [entrada]
    assert search_lancamentos(company_id=admin_user.company_id, filters={"valor_gte": "x"}).count() == 2

    qs = LancamentoFinanceiroFilter(
        data={"search": "Despesa", "tipo": LancamentoFinanceiro.TIPO_SAIDA},
        queryset=search_lancamentos(company_id=admin_user.company_id),
    ).qs
    assert qs.count() == 1


@pytest.mark.django_db
def test_search_contas_pagar_caixas_and_filtersets(
    admin_user,
    banco_com_saldo,
    caixa,
    despesa,
    fornecedor,
):
    atrasada = criar_conta_pagar(
        user=admin_user,
        data={
            "fornecedor": fornecedor,
            "descricao": "Energia vencida",
            "categoria": despesa,
            "valor_total": Decimal("100.00"),
            "data_vencimento": timezone.localdate() - timedelta(days=2),
            "observacao": "Conta antiga",
        },
    )
    parcial = criar_conta_pagar(
        user=admin_user,
        data={
            "descricao": "Internet parcial",
            "categoria": despesa,
            "valor_total": Decimal("80.00"),
            "data_vencimento": timezone.localdate(),
        },
    )
    pagar_conta_pagar(
        user=admin_user,
        conta=parcial,
        data={
            "conta_financeira": banco_com_saldo,
            "valor": Decimal("20.00"),
            "forma_pagamento": LancamentoFinanceiro.FORMA_PIX,
        },
    )
    caixa_diario = abrir_caixa(user=admin_user, data={"conta_financeira": caixa})

    assert list(search_contas_pagar(company_id=admin_user.company_id, filters={"situacao": "atrasada"})) == [atrasada]
    assert list(search_contas_pagar(company_id=admin_user.company_id, filters={"situacao": "parcial"})) == [parcial]
    filtered = search_contas_pagar(
        company_id=admin_user.company_id,
        filters={
            "fornecedor": str(fornecedor.pk),
            "categoria": str(despesa.pk),
            "status": ContaPagar.STATUS_ABERTA,
            "data_vencimento_before": str(timezone.localdate()),
            "data_vencimento_after": str(timezone.localdate() - timedelta(days=3)),
            "valor_restante_gte": "1",
            "valor_restante_lte": "150",
            "search": "Energia",
        },
    )
    assert list(filtered) == [atrasada]
    assert search_contas_pagar(company_id=admin_user.company_id, filters={"valor_restante_lte": "x"}).count() == 2

    assert list(
        search_caixas(
            company_id=admin_user.company_id,
            filters={
                "data": str(timezone.localdate()),
                "status": CaixaDiario.STATUS_ABERTO,
                "conta_financeira": str(caixa.pk),
            },
        )
    ) == [caixa_diario]
    assert search_caixas(company_id=admin_user.company_id, filters=None).count() == 1

    contas_qs = ContaPagarFilter(
        data={"search": "Internet", "situacao": "parcial"},
        queryset=search_contas_pagar(company_id=admin_user.company_id),
    ).qs
    caixas_qs = CaixaDiarioFilter(
        data={"status": CaixaDiario.STATUS_ABERTO},
        queryset=search_caixas(company_id=admin_user.company_id),
    ).qs
    assert list(contas_qs) == [parcial]
    assert list(caixas_qs) == [caixa_diario]
