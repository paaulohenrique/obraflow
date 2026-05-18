from decimal import Decimal
import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from .conftest import make_cliente, VALID_CPF_1, VALID_CNPJ_1, COMPANY_A, COMPANY_B


@pytest.mark.django_db
class TestClienteModel:
    def test_str_representation(self, cliente):
        assert VALID_CPF_1 in str(cliente)
        assert "João da Silva" in str(cliente)

    def test_inherits_base_model_fields(self, cliente):
        assert hasattr(cliente, "id")
        assert hasattr(cliente, "created_at")
        assert hasattr(cliente, "updated_at")
        assert hasattr(cliente, "deleted_at")
        assert hasattr(cliente, "is_active")
        assert hasattr(cliente, "company_id")  # FK column

    def test_default_values(self, empresa_a):
        c = Cliente.objects.create(
            company=empresa_a,
            nome="Defaults Test",
            tipo_pessoa=Cliente.TIPO_PF,
            cpf_cnpj=VALID_CPF_1,
        )
        assert c.saldo_devedor == Decimal("0.00")
        assert c.limite_credito == Decimal("0.00")
        assert c.bloqueado is False
        assert c.is_active is True
        assert c.deleted_at is None

    def test_credito_disponivel_property(self, empresa_a):
        c = make_cliente(
            empresa=empresa_a,
            limite_credito=Decimal("1000.00"),
            saldo_devedor=Decimal("300.00"),
        )
        assert c.credito_disponivel == Decimal("700.00")

    def test_credito_disponivel_never_negative(self, empresa_a):
        c = make_cliente(
            empresa=empresa_a,
            limite_credito=Decimal("100.00"),
            saldo_devedor=Decimal("200.00"),
        )
        assert c.credito_disponivel == Decimal("0.00")

    def test_inadimplente_property_true(self, cliente_inadimplente):
        assert cliente_inadimplente.inadimplente is True

    def test_inadimplente_property_false(self, cliente):
        assert cliente.inadimplente is False

    def test_soft_delete(self, cliente):
        assert cliente.is_deleted is False
        cliente.soft_delete()
        cliente.refresh_from_db()
        assert cliente.is_deleted is True
        assert cliente.is_active is False
        assert cliente.deleted_at is not None

    def test_restore(self, cliente):
        cliente.soft_delete()
        cliente.restore()
        cliente.refresh_from_db()
        assert cliente.is_deleted is False
        assert cliente.is_active is True
        assert cliente.deleted_at is None

    def test_tipo_pf(self, empresa_a):
        c = make_cliente(empresa=empresa_a, tipo_pessoa=Cliente.TIPO_PF)
        assert c.tipo_pessoa == "PF"

    def test_tipo_pj(self, cliente_pj):
        assert cliente_pj.tipo_pessoa == "PJ"

    def test_unique_cpf_cnpj_per_company(self, empresa_a, cliente):
        with pytest.raises(Exception):  # IntegrityError from unique constraint
            make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_1, nome="Duplicado")

    def test_same_cpf_different_company_allowed(self, empresa_a, empresa_b, cliente):
        other = make_cliente(
            empresa=empresa_b,
            cpf_cnpj=VALID_CPF_1,
            nome="Mesmo CPF outra empresa",
        )
        assert other.pk is not None

    def test_same_cpf_after_soft_delete_allowed(self, empresa_a):
        c1 = make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_1)
        c1.soft_delete()
        c2 = make_cliente(empresa=empresa_a, cpf_cnpj=VALID_CPF_1)
        assert c2.pk is not None

    def test_company_fk_is_set(self, cliente, empresa_a):
        assert cliente.company_id == empresa_a.pk
        assert cliente.company == empresa_a

    def test_indexes_exist(self):
        indexed_fields = [tuple(idx.fields) for idx in Cliente._meta.indexes]
        assert ("cpf_cnpj",) in indexed_fields
