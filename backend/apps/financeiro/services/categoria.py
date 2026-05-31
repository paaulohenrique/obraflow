from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.empresas.models import Empresa

from ..models import CategoriaFinanceira, LancamentoFinanceiro


DEFAULT_CATEGORIES = (
    ("Fiado", CategoriaFinanceira.TIPO_RECEITA),
    ("Venda", CategoriaFinanceira.TIPO_RECEITA),
    ("Outros", CategoriaFinanceira.TIPO_RECEITA),
    ("Fornecedor", CategoriaFinanceira.TIPO_DESPESA),
    ("Aluguel", CategoriaFinanceira.TIPO_DESPESA),
    ("Energia", CategoriaFinanceira.TIPO_DESPESA),
    ("Internet", CategoriaFinanceira.TIPO_DESPESA),
    ("Frete", CategoriaFinanceira.TIPO_DESPESA),
    ("Combustível", CategoriaFinanceira.TIPO_DESPESA),
    ("Manutenção", CategoriaFinanceira.TIPO_DESPESA),
    ("Outros", CategoriaFinanceira.TIPO_DESPESA),
    ("Estorno de Receita", CategoriaFinanceira.TIPO_DESPESA),
    ("Estorno de Despesa", CategoriaFinanceira.TIPO_RECEITA),
)


def categoria_snapshot(categoria: CategoriaFinanceira) -> dict[str, Any]:
    return {
        "id": str(categoria.pk),
        "company_id": str(categoria.company_id),
        "nome": categoria.nome,
        "tipo": categoria.tipo,
        "descricao": categoria.descricao,
        "ativa": categoria.ativa,
        "is_active": categoria.is_active,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _ensure_same_company(*, obj, company_id: Any, field: str) -> None:
    if obj and obj.company_id != company_id:
        raise ValidationError({field: "Objeto não pertence à empresa do usuário."})


def _save_model(obj, *, update_fields: list[str]) -> None:
    obj.full_clean()
    obj.save(update_fields=[*update_fields, "updated_at"])


@transaction.atomic
def criar_categoria_financeira(*, user, data: dict[str, Any], request=None) -> CategoriaFinanceira:
    require_company(user)
    categoria = CategoriaFinanceira(
        company=user.company,
        nome=data["nome"],
        tipo=data["tipo"],
        descricao=data.get("descricao", ""),
        ativa=data.get("ativa", True),
    )
    _full_clean_or_400(categoria)
    categoria.save()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=categoria,
        after=categoria_snapshot(categoria),
        request=request,
    )
    return categoria


@transaction.atomic
def update_categoria_financeira(
    *,
    user,
    categoria: CategoriaFinanceira,
    data: dict[str, Any],
    request=None,
) -> CategoriaFinanceira:
    require_company(user)
    _ensure_same_company(obj=categoria, company_id=user.company_id, field="categoria")
    categoria = CategoriaFinanceira.objects.select_for_update().get(
        pk=categoria.pk,
        company_id=user.company_id,
        deleted_at__isnull=True,
    )
    before = categoria_snapshot(categoria)
    for field in ("nome", "tipo", "descricao", "ativa"):
        if field in data:
            setattr(categoria, field, data[field])
    _save_model(categoria, update_fields=["nome", "tipo", "descricao", "ativa"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=categoria,
        before=before,
        after=categoria_snapshot(categoria),
        request=request,
    )
    return categoria


@transaction.atomic
def criar_categorias_padrao_empresa(company: Empresa) -> list[CategoriaFinanceira]:
    categorias = []
    for nome, tipo in DEFAULT_CATEGORIES:
        categoria, _ = CategoriaFinanceira.objects.get_or_create(
            company=company,
            nome=nome,
            tipo=tipo,
            deleted_at=None,
            defaults={"ativa": True, "descricao": "Categoria padrão"},
        )
        categorias.append(categoria)
    return categorias


def get_categoria_padrao(*, company: Empresa, nome: str, tipo: str) -> CategoriaFinanceira:
    criar_categorias_padrao_empresa(company)
    return CategoriaFinanceira.objects.get(
        company=company,
        nome=nome,
        tipo=tipo,
        deleted_at__isnull=True,
    )


@transaction.atomic
def inativar_categoria_financeira(
    *,
    user,
    categoria: CategoriaFinanceira,
    request=None,
) -> CategoriaFinanceira:
    require_company(user)
    _ensure_same_company(obj=categoria, company_id=user.company_id, field="categoria")
    categoria = CategoriaFinanceira.objects.select_for_update().get(
        pk=categoria.pk,
        company_id=user.company_id,
        deleted_at__isnull=True,
    )
    if LancamentoFinanceiro.objects.filter(
        company_id=user.company_id,
        categoria=categoria,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({"categoria": "Categoria com lançamentos não pode ser inativada."})

    before = categoria_snapshot(categoria)
    categoria.ativa = False
    categoria.is_active = False
    _save_model(categoria, update_fields=["ativa", "is_active"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=categoria,
        before=before,
        after=categoria_snapshot(categoria),
        request=request,
    )
    return categoria
