from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, F, Q, QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from .models import (
    CategoriaProduto,
    FormaVendaProduto,
    Fornecedor,
    MovimentacaoEstoque,
    Produto,
    UnidadeMedida,
)


def _require_company_id(company_id: Any) -> None:
    if company_id is None:
        raise PermissionDenied("Usuário sem empresa associada.")


def _active_qs(model, company_id: Any) -> QuerySet:
    _require_company_id(company_id)
    return model.objects.filter(company_id=company_id, deleted_at__isnull=True)


def get_unidade_by_id(*, company_id: Any, unidade_id: uuid.UUID) -> UnidadeMedida:
    try:
        return _active_qs(UnidadeMedida, company_id).get(pk=unidade_id)
    except (UnidadeMedida.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Unidade de medida não encontrada.")


def get_categoria_by_id(*, company_id: Any, categoria_id: uuid.UUID) -> CategoriaProduto:
    try:
        return _active_qs(CategoriaProduto, company_id).get(pk=categoria_id)
    except (CategoriaProduto.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Categoria não encontrada.")


def get_fornecedor_by_id(*, company_id: Any, fornecedor_id: uuid.UUID) -> Fornecedor:
    try:
        return _active_qs(Fornecedor, company_id).get(pk=fornecedor_id)
    except (Fornecedor.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Fornecedor não encontrado.")


def get_produto_by_id(*, company_id: Any, produto_id: uuid.UUID) -> Produto:
    try:
        return (
            _active_qs(Produto, company_id)
            .select_related("categoria", "fornecedor_principal", "unidade")
            .get(pk=produto_id)
        )
    except (Produto.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Produto não encontrado.")


def get_movimentacao_by_id(*, company_id: Any, movimentacao_id: uuid.UUID) -> MovimentacaoEstoque:
    try:
        return (
            _active_qs(MovimentacaoEstoque, company_id)
            .select_related("produto", "fornecedor", "created_by", "movimentacao_cancelada")
            .get(pk=movimentacao_id)
        )
    except (MovimentacaoEstoque.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Movimentação não encontrada.")


def get_unidades(*, company_id: Any) -> QuerySet:
    return _active_qs(UnidadeMedida, company_id).order_by("nome")


def get_categorias(*, company_id: Any) -> QuerySet:
    return _active_qs(CategoriaProduto, company_id).order_by("nome")


def get_fornecedores(*, company_id: Any) -> QuerySet:
    return _active_qs(Fornecedor, company_id).order_by("razao_social")


def get_produtos(*, company_id: Any) -> QuerySet:
    return (
        _active_qs(Produto, company_id)
        .select_related("categoria", "fornecedor_principal", "unidade")
    )


def get_forma_venda_by_id(*, company_id: Any, forma_venda_id: uuid.UUID) -> FormaVendaProduto:
    try:
        return (
            _active_qs(FormaVendaProduto, company_id)
            .select_related("produto", "produto__unidade")
            .get(pk=forma_venda_id)
        )
    except (FormaVendaProduto.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Forma de venda não encontrada.")


def get_formas_venda(*, company_id: Any, produto_id: uuid.UUID | None = None) -> QuerySet:
    qs = _active_qs(FormaVendaProduto, company_id).select_related("produto", "produto__unidade")
    if produto_id is not None:
        qs = qs.filter(produto_id=produto_id)
    return qs.order_by("produto__nome", "nome")


def get_movimentacoes(*, company_id: Any) -> QuerySet:
    return (
        _active_qs(MovimentacaoEstoque, company_id)
        .select_related("produto", "fornecedor", "created_by", "movimentacao_cancelada")
    )


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes", "sim"):
            return True
        if value.lower() in ("false", "0", "no", "nao", "não"):
            return False
    return None


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def search_produtos(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = get_produtos(company_id=company_id)
    if not filters:
        return qs

    if q := filters.get("search"):
        qs = qs.filter(
            Q(nome__icontains=q)
            | Q(sku__icontains=q)
            | Q(codigo_barras__icontains=q)
            | Q(descricao__icontains=q)
        )
    if categoria := filters.get("categoria"):
        qs = qs.filter(categoria_id=categoria)
    if fornecedor := filters.get("fornecedor"):
        qs = qs.filter(fornecedor_principal_id=fornecedor)
    if unidade := filters.get("unidade"):
        qs = qs.filter(unidade_id=unidade)

    is_active = _parse_bool(filters.get("is_active"))
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    estoque_baixo = _parse_bool(filters.get("estoque_baixo"))
    if estoque_baixo is True:
        qs = qs.filter(estoque_atual__lte=F("estoque_minimo"))
    elif estoque_baixo is False:
        qs = qs.filter(estoque_atual__gt=F("estoque_minimo"))

    if (gte := filters.get("preco_venda__gte")) is not None:
        value = _decimal(gte)
        if value is not None:
            qs = qs.filter(preco_venda__gte=value)
    if (lte := filters.get("preco_venda__lte")) is not None:
        value = _decimal(lte)
        if value is not None:
            qs = qs.filter(preco_venda__lte=value)

    return qs


def produtos_baixo_estoque(*, company_id: Any) -> QuerySet:
    return get_produtos(company_id=company_id).filter(
        estoque_atual__lte=F("estoque_minimo"),
        is_active=True,
    )


def auditoria_produtos_operacionais(*, company_id: Any) -> dict[str, Any]:
    qs = get_produtos(company_id=company_id).annotate(
        formas_ativas=Count(
            "formas_venda",
            filter=Q(
                formas_venda__ativo=True,
                formas_venda__deleted_at__isnull=True,
            ),
            distinct=True,
        )
    )

    grupos = {
        "sem_forma_venda": qs.filter(is_active=True, formas_ativas=0),
        "sem_categoria": qs.filter(categoria__isnull=True),
        "sem_unidade": qs.filter(unidade__isnull=True),
        "sem_preco": qs.filter(is_active=True, preco_venda__lte=Decimal("0.00")),
        "inativos": qs.filter(is_active=False),
    }

    def resumir(item: Produto) -> dict[str, Any]:
        return {
            "id": str(item.pk),
            "nome": item.nome,
            "sku": item.sku,
            "categoria_nome": item.categoria.nome if item.categoria_id else "",
            "unidade_sigla": item.unidade.sigla if item.unidade_id else "",
            "preco_venda": item.preco_venda,
            "estoque_atual": item.estoque_atual,
            "is_active": item.is_active,
        }

    return {
        chave: {
            "count": grupo.count(),
            "results": [resumir(item) for item in grupo.order_by("nome")[:10]],
        }
        for chave, grupo in grupos.items()
    }


def search_movimentacoes(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = get_movimentacoes(company_id=company_id)
    if not filters:
        return qs

    if produto := filters.get("produto"):
        qs = qs.filter(produto_id=produto)
    if tipo := filters.get("tipo"):
        qs = qs.filter(tipo=tipo)
    if status := filters.get("status"):
        qs = qs.filter(status=status)
    if fornecedor := filters.get("fornecedor"):
        qs = qs.filter(fornecedor_id=fornecedor)
    if created_by := filters.get("created_by"):
        qs = qs.filter(created_by_id=created_by)
    if created_at_after := filters.get("created_at_after"):
        qs = qs.filter(created_at__gte=created_at_after)
    if created_at_before := filters.get("created_at_before"):
        qs = qs.filter(created_at__lte=created_at_before)

    return qs
