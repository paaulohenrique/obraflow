from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.empresas.models import Empresa
from .conftest import _make_empresa, VALID_CNPJ_A, VALID_CNPJ_B


@pytest.mark.django_db
class TestEmpresaModel:
    def test_str_representation(self):
        e = _make_empresa()
        assert "Empresa Alpha" in str(e)

    def test_inherits_base_model_fields(self):
        e = _make_empresa()
        assert hasattr(e, "id")
        assert hasattr(e, "created_at")
        assert hasattr(e, "updated_at")
        assert hasattr(e, "deleted_at")
        assert hasattr(e, "is_active")

    def test_default_values(self):
        e = _make_empresa()
        assert e.is_active is True
        assert e.deleted_at is None
        assert e.plano == Empresa.PLANO_BASICO
        assert e.limite_usuarios == 10

    def test_soft_delete(self):
        e = _make_empresa()
        e.soft_delete()
        e.refresh_from_db()
        assert e.is_deleted is True
        assert e.is_active is False
        assert e.deleted_at is not None

    def test_restore(self):
        e = _make_empresa()
        e.soft_delete()
        e.restore()
        e.refresh_from_db()
        assert e.is_deleted is False
        assert e.is_active is True
        assert e.deleted_at is None

    def test_cnpj_unique(self):
        _make_empresa(cnpj=VALID_CNPJ_A)
        with pytest.raises(Exception):
            _make_empresa(cnpj=VALID_CNPJ_A, razao_social="Outra")

    def test_planos_choices(self):
        for plano in (Empresa.PLANO_BASICO, Empresa.PLANO_PROFISSIONAL, Empresa.PLANO_ENTERPRISE):
            e = Empresa(
                razao_social="X",
                cnpj="00000000000" + str(hash(plano))[-3:],
                plano=plano,
            )
            assert e.plano == plano

    def test_total_usuarios_via_related(self, empresa_alpha):
        assert empresa_alpha.usuarios.count() == 0

    def test_clientes_via_related(self, empresa_alpha):
        assert empresa_alpha.clientes.count() == 0
