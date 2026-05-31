from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.empresas.validators import clean_cnpj
from apps.estoque.models import (
    CategoriaProduto,
    Fornecedor,
    Produto,
    UnidadeMedida,
)


def _base_snapshot(obj) -> dict[str, Any]:
    data = {
        "id": str(obj.pk),
        "company_id": str(obj.company_id),
        "is_active": obj.is_active,
    }
    if hasattr(obj, "nome"):
        data["nome"] = obj.nome
    return data


def _unidade_snapshot(unidade: UnidadeMedida) -> dict[str, Any]:
    return {
        **_base_snapshot(unidade),
        "sigla": unidade.sigla,
        "descricao": unidade.descricao,
    }


def _categoria_snapshot(categoria: CategoriaProduto) -> dict[str, Any]:
    return {
        **_base_snapshot(categoria),
        "descricao": categoria.descricao,
    }


def _fornecedor_snapshot(fornecedor: Fornecedor) -> dict[str, Any]:
    return {
        **_base_snapshot(fornecedor),
        "razao_social": fornecedor.razao_social,
        "nome_fantasia": fornecedor.nome_fantasia,
        "cnpj": fornecedor.cnpj,
        "telefone": fornecedor.telefone,
        "email": fornecedor.email,
    }


def produto_snapshot(produto: Produto) -> dict[str, Any]:
    return {
        **_base_snapshot(produto),
        "descricao": produto.descricao,
        "sku": produto.sku,
        "codigo_barras": produto.codigo_barras,
        "categoria_id": str(produto.categoria_id),
        "fornecedor_principal_id": (
            str(produto.fornecedor_principal_id) if produto.fornecedor_principal_id else None
        ),
        "unidade_id": str(produto.unidade_id),
        "preco_compra": str(produto.preco_compra),
        "preco_venda": str(produto.preco_venda),
        "custo_medio": str(produto.custo_medio),
        "estoque_atual": str(produto.estoque_atual),
        "estoque_minimo": str(produto.estoque_minimo),
    }


def _ensure_same_company(*, obj, company_id: Any, field: str) -> None:
    if obj and obj.company_id != company_id:
        raise ValidationError({field: "Objeto não pertence à empresa do usuário."})


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _validate_produto_relations(*, company_id: Any, data: dict[str, Any]) -> None:
    _ensure_same_company(obj=data.get("categoria"), company_id=company_id, field="categoria")
    _ensure_same_company(
        obj=data.get("fornecedor_principal"),
        company_id=company_id,
        field="fornecedor_principal",
    )
    _ensure_same_company(obj=data.get("unidade"), company_id=company_id, field="unidade")


def _check_unique_produto(
    *,
    company_id: Any,
    sku: str = "",
    codigo_barras: str = "",
    exclude_pk=None,
) -> None:
    if sku:
        qs = Produto.objects.filter(company_id=company_id, sku=sku, deleted_at__isnull=True)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if qs.exists():
            raise ValidationError({"sku": "SKU já cadastrado nesta empresa."})

    if codigo_barras:
        qs = Produto.objects.filter(
            company_id=company_id,
            codigo_barras=codigo_barras,
            deleted_at__isnull=True,
        )
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if qs.exists():
            raise ValidationError({"codigo_barras": "Código de barras já cadastrado nesta empresa."})


@transaction.atomic
def create_unidade(*, user, data: dict[str, Any], request=None) -> UnidadeMedida:
    require_company(user)
    unidade = UnidadeMedida(company=user.company, **data)
    _full_clean_or_400(unidade)
    unidade.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=unidade,
        after=_unidade_snapshot(unidade),
        request=request,
    )
    return unidade


@transaction.atomic
def update_unidade(*, user, unidade: UnidadeMedida, data: dict[str, Any], request=None) -> UnidadeMedida:
    require_company(user)
    _ensure_same_company(obj=unidade, company_id=user.company_id, field="unidade")
    before = _unidade_snapshot(unidade)
    for field in ("nome", "sigla", "descricao"):
        if field in data:
            setattr(unidade, field, data[field])
    _full_clean_or_400(unidade)
    unidade.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=unidade,
        before=before,
        after=_unidade_snapshot(unidade),
        request=request,
    )
    return unidade


@transaction.atomic
def soft_delete_unidade(*, user, unidade: UnidadeMedida, request=None) -> None:
    require_company(user)
    _ensure_same_company(obj=unidade, company_id=user.company_id, field="unidade")
    before = _unidade_snapshot(unidade)
    unidade.soft_delete()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=unidade,
        before=before,
        request=request,
    )


@transaction.atomic
def create_categoria(*, user, data: dict[str, Any], request=None) -> CategoriaProduto:
    require_company(user)
    categoria = CategoriaProduto(company=user.company, **data)
    _full_clean_or_400(categoria)
    categoria.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=categoria,
        after=_categoria_snapshot(categoria),
        request=request,
    )
    return categoria


@transaction.atomic
def update_categoria(
    *, user, categoria: CategoriaProduto, data: dict[str, Any], request=None
) -> CategoriaProduto:
    require_company(user)
    _ensure_same_company(obj=categoria, company_id=user.company_id, field="categoria")
    before = _categoria_snapshot(categoria)
    for field in ("nome", "descricao"):
        if field in data:
            setattr(categoria, field, data[field])
    _full_clean_or_400(categoria)
    categoria.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=categoria,
        before=before,
        after=_categoria_snapshot(categoria),
        request=request,
    )
    return categoria


@transaction.atomic
def soft_delete_categoria(*, user, categoria: CategoriaProduto, request=None) -> None:
    require_company(user)
    _ensure_same_company(obj=categoria, company_id=user.company_id, field="categoria")
    before = _categoria_snapshot(categoria)
    categoria.soft_delete()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=categoria,
        before=before,
        request=request,
    )


@transaction.atomic
def create_fornecedor(*, user, data: dict[str, Any], request=None) -> Fornecedor:
    require_company(user)
    data = {**data, "cnpj": clean_cnpj(data.get("cnpj", ""))}
    fornecedor = Fornecedor(company=user.company, **data)
    _full_clean_or_400(fornecedor)
    fornecedor.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=fornecedor,
        after=_fornecedor_snapshot(fornecedor),
        request=request,
    )
    return fornecedor


@transaction.atomic
def update_fornecedor(
    *, user, fornecedor: Fornecedor, data: dict[str, Any], request=None
) -> Fornecedor:
    require_company(user)
    _ensure_same_company(obj=fornecedor, company_id=user.company_id, field="fornecedor")
    before = _fornecedor_snapshot(fornecedor)
    if "cnpj" in data:
        data = {**data, "cnpj": clean_cnpj(data["cnpj"])}
    updatable = {
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "telefone",
        "email",
        "observacoes",
    }
    for field, value in data.items():
        if field in updatable:
            setattr(fornecedor, field, value)
    _full_clean_or_400(fornecedor)
    fornecedor.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=fornecedor,
        before=before,
        after=_fornecedor_snapshot(fornecedor),
        request=request,
    )
    return fornecedor


@transaction.atomic
def soft_delete_fornecedor(*, user, fornecedor: Fornecedor, request=None) -> None:
    require_company(user)
    _ensure_same_company(obj=fornecedor, company_id=user.company_id, field="fornecedor")
    before = _fornecedor_snapshot(fornecedor)
    fornecedor.soft_delete()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=fornecedor,
        before=before,
        request=request,
    )


@transaction.atomic
def create_produto(*, user, data: dict[str, Any], request=None) -> Produto:
    require_company(user)
    company_id = user.company_id
    _validate_produto_relations(company_id=company_id, data=data)

    sku = (data.get("sku") or "").strip().upper()
    codigo_barras = (data.get("codigo_barras") or "").strip()
    _check_unique_produto(company_id=company_id, sku=sku, codigo_barras=codigo_barras)

    produto = Produto(company=user.company, **{**data, "sku": sku, "codigo_barras": codigo_barras})
    _full_clean_or_400(produto)
    produto.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=produto,
        after=produto_snapshot(produto),
        request=request,
    )
    return produto


@transaction.atomic
def update_produto(*, user, produto: Produto, data: dict[str, Any], request=None) -> Produto:
    require_company(user)
    _ensure_same_company(obj=produto, company_id=user.company_id, field="produto")
    _validate_produto_relations(company_id=user.company_id, data=data)

    before = produto_snapshot(produto)
    next_sku = (data.get("sku", produto.sku) or "").strip().upper()
    next_barcode = (data.get("codigo_barras", produto.codigo_barras) or "").strip()
    _check_unique_produto(
        company_id=user.company_id,
        sku=next_sku,
        codigo_barras=next_barcode,
        exclude_pk=produto.pk,
    )

    updatable = {
        "nome",
        "descricao",
        "sku",
        "codigo_barras",
        "categoria",
        "fornecedor_principal",
        "unidade",
        "preco_compra",
        "preco_venda",
        "custo_medio",
        "estoque_minimo",
    }
    for field, value in data.items():
        if field in updatable:
            setattr(produto, field, value)
    produto.sku = next_sku
    produto.codigo_barras = next_barcode
    _full_clean_or_400(produto)
    produto.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=produto,
        before=before,
        after=produto_snapshot(produto),
        request=request,
    )
    return produto


@transaction.atomic
def inativar_produto(*, user, produto: Produto, request=None) -> Produto:
    require_company(user)
    _ensure_same_company(obj=produto, company_id=user.company_id, field="produto")
    if not produto.is_active:
        raise ValidationError({"is_active": "Produto já está inativo."})

    before = produto_snapshot(produto)
    produto.is_active = False
    produto.save(update_fields=["is_active", "updated_at"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=produto,
        before=before,
        after=produto_snapshot(produto),
        request=request,
    )
    return produto


@transaction.atomic
def ativar_produto(*, user, produto: Produto, request=None) -> Produto:
    require_company(user)
    _ensure_same_company(obj=produto, company_id=user.company_id, field="produto")
    if produto.is_active:
        raise ValidationError({"is_active": "Produto já está ativo."})

    before = produto_snapshot(produto)
    produto.is_active = True
    produto.save(update_fields=["is_active", "updated_at"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=produto,
        before=before,
        after=produto_snapshot(produto),
        request=request,
    )
    return produto


@transaction.atomic
def soft_delete_produto(*, user, produto: Produto, request=None) -> None:
    require_company(user)
    _ensure_same_company(obj=produto, company_id=user.company_id, field="produto")
    before = produto_snapshot(produto)
    produto.soft_delete()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=produto,
        before=before,
        request=request,
    )
