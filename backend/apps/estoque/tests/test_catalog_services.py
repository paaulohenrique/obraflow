import pytest
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.estoque.services import (
    create_categoria,
    create_fornecedor,
    create_unidade,
    soft_delete_fornecedor,
    soft_delete_unidade,
    update_categoria,
    update_fornecedor,
    update_unidade,
)
from .conftest import make_categoria, make_fornecedor, make_unidade


@pytest.mark.django_db
def test_unidade_services_create_update_delete(admin_user):
    unidade = create_unidade(
        user=admin_user,
        data={"nome": "Peça", "sigla": "pc", "descricao": "Peça unitária"},
    )
    updated = update_unidade(
        user=admin_user,
        unidade=unidade,
        data={"nome": "Peça atualizada", "sigla": "pç"},
    )
    soft_delete_unidade(user=admin_user, unidade=updated)
    updated.refresh_from_db()

    assert updated.sigla == "PÇ"
    assert updated.is_deleted is True
    assert AuditLog.objects.filter(entity_type="UnidadeMedida", entity_id=updated.pk).count() == 3


@pytest.mark.django_db
def test_categoria_services_update_and_cross_company(admin_user, other_company_user):
    categoria = create_categoria(user=admin_user, data={"nome": "Tubos"})
    updated = update_categoria(
        user=admin_user,
        categoria=categoria,
        data={"nome": "Tubos e conexões", "descricao": "PVC"},
    )

    assert updated.nome == "Tubos e conexões"
    with pytest.raises(ValidationError, match="empresa"):
        update_categoria(
            user=other_company_user,
            categoria=updated,
            data={"nome": "Não pode"},
        )


@pytest.mark.django_db
def test_fornecedor_services_create_update_delete_and_invalid_cnpj(admin_user):
    fornecedor = create_fornecedor(
        user=admin_user,
        data={
            "razao_social": "Fornecedor Service",
            "nome_fantasia": "Service",
            "cnpj": "45.997.418/0001-53",
        },
    )
    updated = update_fornecedor(
        user=admin_user,
        fornecedor=fornecedor,
        data={"telefone": "85999990000", "observacoes": "Preferencial"},
    )
    soft_delete_fornecedor(user=admin_user, fornecedor=updated)
    updated.refresh_from_db()

    assert updated.cnpj == "45997418000153"
    assert updated.telefone == "85999990000"
    assert updated.is_deleted is True

    with pytest.raises(ValidationError, match="CNPJ"):
        create_fornecedor(
            user=admin_user,
            data={"razao_social": "Inválido", "cnpj": "00000000000000"},
        )


@pytest.mark.django_db
def test_duplicate_catalog_constraints_return_validation(admin_user, empresa_a):
    make_unidade(empresa_a, nome="Unidade Existente", sigla="UNX")
    make_categoria(empresa_a, nome="Categoria Existente")
    make_fornecedor(empresa_a, razao_social="Fornecedor Existente", cnpj="45997418000153")

    with pytest.raises(ValidationError):
        create_unidade(user=admin_user, data={"nome": "Outra", "sigla": "UNX"})
    with pytest.raises(ValidationError):
        create_categoria(user=admin_user, data={"nome": "Categoria Existente"})
    with pytest.raises(ValidationError):
        create_fornecedor(
            user=admin_user,
            data={"razao_social": "Outro", "cnpj": "45997418000153"},
        )
