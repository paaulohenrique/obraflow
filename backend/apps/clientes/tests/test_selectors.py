from decimal import Decimal

import pytest
from rest_framework.exceptions import NotFound

from apps.clientes.selectors import (
    get_cliente_by_id,
    get_cliente_by_documento,
    get_clientes_ativos,
    get_clientes_bloqueados,
    get_clientes_inadimplentes,
    search_clientes,
)
from .conftest import COMPANY_A, COMPANY_B, VALID_CPF_1, VALID_CPF_2, make_cliente


@pytest.mark.django_db
class TestGetClienteById:
    def test_found(self, cliente, empresa_a):
        result = get_cliente_by_id(company_id=empresa_a.pk, cliente_id=cliente.pk)
        assert result.pk == cliente.pk

    def test_not_found_raises(self, empresa_a):
        import uuid
        with pytest.raises(NotFound):
            get_cliente_by_id(company_id=empresa_a.pk, cliente_id=uuid.uuid4())

    def test_wrong_company_raises(self, cliente, empresa_b):
        with pytest.raises(NotFound):
            get_cliente_by_id(company_id=empresa_b.pk, cliente_id=cliente.pk)

    def test_soft_deleted_not_found(self, cliente, empresa_a):
        cliente.soft_delete()
        with pytest.raises(NotFound):
            get_cliente_by_id(company_id=empresa_a.pk, cliente_id=cliente.pk)

    def test_malformed_uuid_raises_not_found(self, empresa_a):
        with pytest.raises(NotFound):
            get_cliente_by_id(company_id=empresa_a.pk, cliente_id="nao-e-uuid")


@pytest.mark.django_db
class TestGetClienteByDocumento:
    def test_found(self, cliente, empresa_a):
        result = get_cliente_by_documento(company_id=empresa_a.pk, cpf_cnpj=VALID_CPF_1)
        assert result.pk == cliente.pk

    def test_not_found_returns_none(self, empresa_a):
        result = get_cliente_by_documento(company_id=empresa_a.pk, cpf_cnpj="99999999999")
        assert result is None

    def test_wrong_company_returns_none(self, cliente, empresa_b):
        result = get_cliente_by_documento(company_id=empresa_b.pk, cpf_cnpj=VALID_CPF_1)
        assert result is None


@pytest.mark.django_db
class TestGetClientesAtivos:
    def test_returns_only_active(self, cliente, cliente_bloqueado, cliente_inadimplente, empresa_a):
        qs = get_clientes_ativos(company_id=empresa_a.pk)
        assert qs.count() == 3

    def test_excludes_soft_deleted(self, cliente, empresa_a):
        cliente.soft_delete()
        qs = get_clientes_ativos(company_id=empresa_a.pk)
        assert qs.count() == 0

    def test_tenant_isolation(self, cliente, cliente_outra_empresa, empresa_a):
        qs = get_clientes_ativos(company_id=empresa_a.pk)
        ids = list(qs.values_list("pk", flat=True))
        assert cliente.pk in ids
        assert cliente_outra_empresa.pk not in ids


@pytest.mark.django_db
class TestSearchClientes:
    def test_search_by_nome(self, cliente, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"search": "João"})
        assert qs.count() == 1

    def test_search_by_cpf(self, cliente, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"search": VALID_CPF_1[:5]})
        assert qs.count() == 1

    def test_search_no_results(self, cliente, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"search": "xyz_notexist"})
        assert qs.count() == 0

    def test_filter_bloqueado(self, cliente, cliente_bloqueado, cliente_inadimplente, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"bloqueado": True})
        assert qs.count() == 1
        assert qs.first().pk == cliente_bloqueado.pk

    def test_filter_tipo_pessoa(self, cliente, cliente_pj, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"tipo_pessoa": "PF"})
        assert all(c.tipo_pessoa == "PF" for c in qs)

    def test_filter_cidade(self, cliente, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"cidade": "São Paulo"})
        assert qs.count() == 1

    def test_filter_saldo_devedor_gt(self, cliente, cliente_inadimplente, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk, filters={"saldo_devedor__gt": 0})
        assert qs.count() == 1
        assert qs.first().pk == cliente_inadimplente.pk

    def test_no_filters(self, cliente, cliente_bloqueado, empresa_a):
        qs = search_clientes(company_id=empresa_a.pk)
        assert qs.count() == 2


@pytest.mark.django_db
class TestGetClientesBloqueados:
    def test_returns_only_bloqueados(self, cliente, cliente_bloqueado, empresa_a):
        qs = get_clientes_bloqueados(company_id=empresa_a.pk)
        assert qs.count() == 1
        assert qs.first().pk == cliente_bloqueado.pk

    def test_tenant_isolation(self, cliente_bloqueado, empresa_b):
        qs = get_clientes_bloqueados(company_id=empresa_b.pk)
        assert qs.count() == 0


@pytest.mark.django_db
class TestGetClientesInadimplentes:
    def test_returns_only_inadimplentes(self, cliente, cliente_inadimplente, empresa_a):
        qs = get_clientes_inadimplentes(company_id=empresa_a.pk)
        assert qs.count() == 1
        assert qs.first().pk == cliente_inadimplente.pk

    def test_ordered_by_saldo_devedor_desc(self, empresa_a):
        c1 = make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_1, saldo_devedor=Decimal("100.00"))
        c2 = make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_2, saldo_devedor=Decimal("500.00"))
        qs = list(get_clientes_inadimplentes(company_id=empresa_a.pk))
        assert qs[0].pk == c2.pk
