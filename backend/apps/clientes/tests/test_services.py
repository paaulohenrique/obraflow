from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.clientes.models import Cliente
from apps.clientes.services import (
    create_cliente,
    update_cliente,
    bloquear_cliente,
    desbloquear_cliente,
    soft_delete_cliente,
)
from .conftest import (
    VALID_CPF_1, VALID_CPF_2, VALID_CNPJ_1, make_cliente
)


def _base_data(**kwargs):
    return {
        "nome": "Maria Souza",
        "tipo_pessoa": Cliente.TIPO_PF,
        "cpf_cnpj": VALID_CPF_2,
        "telefone": "(11) 91234-5678",
        "email": "maria@test.com",
        "cidade": "Campinas",
        "estado": "SP",
        "limite_credito": Decimal("500.00"),
        **kwargs,
    }


@pytest.mark.django_db
class TestCreateCliente:
    def test_create_pf_valid(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data())
        assert c.pk is not None
        assert c.cpf_cnpj == VALID_CPF_2
        assert c.telefone == "11912345678"  # normalised
        assert c.company_id == admin_user.company_id

    def test_create_pj_valid(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data(
            tipo_pessoa=Cliente.TIPO_PJ,
            cpf_cnpj=VALID_CNPJ_1,
        ))
        assert c.tipo_pessoa == Cliente.TIPO_PJ
        assert c.cpf_cnpj == VALID_CNPJ_1

    def test_saldo_devedor_always_zero_on_create(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data())
        assert c.saldo_devedor == Decimal("0.00")

    def test_bloqueado_always_false_on_create(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data())
        assert c.bloqueado is False

    def test_invalid_cpf_raises(self, admin_user):
        with pytest.raises(ValidationError, match="CPF"):
            create_cliente(user=admin_user, data=_base_data(cpf_cnpj="00000000000"))

    def test_invalid_cnpj_raises(self, admin_user):
        with pytest.raises(ValidationError, match="CNPJ"):
            create_cliente(user=admin_user, data=_base_data(
                tipo_pessoa=Cliente.TIPO_PJ,
                cpf_cnpj="00000000000000",
            ))

    def test_duplicate_cpf_same_company_raises(self, admin_user, cliente):
        with pytest.raises(ValidationError, match="CPF"):
            create_cliente(user=admin_user, data=_base_data(cpf_cnpj=VALID_CPF_1))

    def test_cpf_stored_without_mask(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data(
            cpf_cnpj="111.444.777-35"
        ))
        assert c.cpf_cnpj == "11144477735"
        assert "." not in c.cpf_cnpj
        assert "-" not in c.cpf_cnpj

    def test_creates_audit_log(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data())
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=c.pk,
            action=AuditLog.ACTION_CREATE,
        ).first()
        assert log is not None
        assert log.user == admin_user
        assert log.after is not None

    def test_company_id_from_user(self, admin_user):
        c = create_cliente(user=admin_user, data=_base_data())
        assert c.company_id == admin_user.company_id


@pytest.mark.django_db
class TestUpdateCliente:
    def test_update_nome(self, admin_user, cliente):
        updated = update_cliente(
            user=admin_user,
            cliente=cliente,
            data={"nome": "Novo Nome"},
        )
        assert updated.nome == "Novo Nome"

    def test_update_preserves_saldo_devedor(self, admin_user):
        c = make_cliente(saldo_devedor=Decimal("200.00"))
        updated = update_cliente(
            user=admin_user,
            cliente=c,
            data={"nome": "Novo Nome"},
        )
        assert updated.saldo_devedor == Decimal("200.00")

    def test_update_cpf_invalid_raises(self, admin_user, cliente):
        with pytest.raises(ValidationError, match="CPF"):
            update_cliente(
                user=admin_user,
                cliente=cliente,
                data={"cpf_cnpj": "00000000000"},
            )

    def test_update_cpf_to_existing_raises(self, admin_user, cliente):
        make_cliente(cpf_cnpj=VALID_CPF_2, nome="Outro")
        with pytest.raises(ValidationError, match="CPF"):
            update_cliente(
                user=admin_user,
                cliente=cliente,
                data={"cpf_cnpj": VALID_CPF_2},
            )

    def test_update_same_cpf_no_raises(self, admin_user, cliente):
        updated = update_cliente(
            user=admin_user,
            cliente=cliente,
            data={"cpf_cnpj": VALID_CPF_1, "nome": "Mesmo CPF"},
        )
        assert updated.cpf_cnpj == VALID_CPF_1

    def test_update_normalises_telefone(self, admin_user, cliente):
        updated = update_cliente(
            user=admin_user,
            cliente=cliente,
            data={"telefone": "(11) 98888-7777"},
        )
        assert updated.telefone == "11988887777"

    def test_update_creates_audit_log(self, admin_user, cliente):
        update_cliente(user=admin_user, cliente=cliente, data={"nome": "X"})
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=cliente.pk,
            action=AuditLog.ACTION_UPDATE,
        ).first()
        assert log is not None
        assert log.before["nome"] == "João da Silva"
        assert log.after["nome"] == "X"


@pytest.mark.django_db
class TestBloquearCliente:
    def test_bloquear(self, admin_user, cliente):
        result = bloquear_cliente(user=admin_user, cliente=cliente)
        assert result.bloqueado is True

    def test_bloquear_ja_bloqueado_raises(self, admin_user, cliente_bloqueado):
        with pytest.raises(ValidationError, match="bloqueado"):
            bloquear_cliente(user=admin_user, cliente=cliente_bloqueado)

    def test_bloquear_creates_audit_log(self, admin_user, cliente):
        bloquear_cliente(user=admin_user, cliente=cliente)
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=cliente.pk,
            action=AuditLog.ACTION_UPDATE,
        ).first()
        assert log is not None
        assert log.before["bloqueado"] is False
        assert log.after["bloqueado"] is True


@pytest.mark.django_db
class TestDesbloquearCliente:
    def test_desbloquear(self, admin_user, cliente_bloqueado):
        result = desbloquear_cliente(user=admin_user, cliente=cliente_bloqueado)
        assert result.bloqueado is False

    def test_desbloquear_nao_bloqueado_raises(self, admin_user, cliente):
        with pytest.raises(ValidationError, match="bloqueado"):
            desbloquear_cliente(user=admin_user, cliente=cliente)

    def test_desbloquear_creates_audit_log(self, admin_user, cliente_bloqueado):
        desbloquear_cliente(user=admin_user, cliente=cliente_bloqueado)
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=cliente_bloqueado.pk,
            action=AuditLog.ACTION_UPDATE,
        ).first()
        assert log is not None


@pytest.mark.django_db
class TestSoftDeleteCliente:
    def test_soft_delete(self, admin_user, cliente):
        soft_delete_cliente(user=admin_user, cliente=cliente)
        cliente.refresh_from_db()
        assert cliente.is_deleted is True
        assert cliente.is_active is False

    def test_soft_delete_creates_audit_log(self, admin_user, cliente):
        soft_delete_cliente(user=admin_user, cliente=cliente)
        log = AuditLog.objects.filter(
            entity_type="Cliente",
            entity_id=cliente.pk,
            action=AuditLog.ACTION_DELETE,
        ).first()
        assert log is not None
