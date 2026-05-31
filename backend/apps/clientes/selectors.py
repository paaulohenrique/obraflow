import logging
from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from .models import Cliente

logger = logging.getLogger("apps.clientes")


def _base_qs(company_id: Any) -> QuerySet:
    """Active (non-deleted) clients scoped to the tenant."""
    if company_id is None:
        logger.error("_base_qs called with company_id=None — tenant isolation broken")
        raise PermissionDenied("Usuário sem empresa associada.")
    return Cliente.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
    )


def get_cliente_by_id(*, company_id: Any, cliente_id: uuid.UUID) -> Cliente:
    try:
        return _base_qs(company_id).get(pk=cliente_id)
    except (Cliente.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Cliente não encontrado.")


def get_cliente_by_documento(*, company_id: Any, cpf_cnpj: str) -> Cliente | None:
    return _base_qs(company_id).filter(cpf_cnpj=cpf_cnpj).first()


def get_clientes_ativos(*, company_id: Any) -> QuerySet:
    return _base_qs(company_id).order_by("nome")


def _parse_bool(value: Any) -> bool | None:
    """Convert string query param values to bool. Returns None if undecidable."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
    return None


def filter_clientes_search(qs: QuerySet, term: str) -> QuerySet:
    """Apply multi-field full-text search to an existing queryset."""
    if not term:
        return qs
    return qs.filter(
        Q(nome__icontains=term)
        | Q(cpf_cnpj__icontains=term)
        | Q(telefone__icontains=term)
        | Q(whatsapp__icontains=term)
        | Q(email__icontains=term)
    )


def search_clientes(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    """Return a filtered queryset for the given company.

    Accepts query-param style dicts (values may be strings). Ordering is NOT
    applied here — callers are responsible for ordering before paginating.
    """
    qs = _base_qs(company_id)
    if not filters:
        return qs

    if q := filters.get("search"):
        qs = filter_clientes_search(qs, q)

    if nome := filters.get("nome"):
        qs = qs.filter(nome__icontains=nome)

    bloqueado = _parse_bool(filters.get("bloqueado"))
    if bloqueado is not None:
        qs = qs.filter(bloqueado=bloqueado)

    if tipo := filters.get("tipo_pessoa"):
        qs = qs.filter(tipo_pessoa=tipo)

    if cidade := filters.get("cidade"):
        qs = qs.filter(cidade__icontains=cidade)

    if estado := filters.get("estado"):
        qs = qs.filter(estado=estado.upper())

    if (saldo_gt := filters.get("saldo_devedor__gt")) is not None:
        try:
            qs = qs.filter(saldo_devedor__gt=Decimal(str(saldo_gt)))
        except (InvalidOperation, ValueError, TypeError):
            pass  # non-numeric query param — silently ignore

    if (saldo_gte := filters.get("saldo_devedor__gte")) is not None:
        try:
            qs = qs.filter(saldo_devedor__gte=Decimal(str(saldo_gte)))
        except (InvalidOperation, ValueError, TypeError):
            pass  # non-numeric query param — silently ignore

    is_active = _parse_bool(filters.get("is_active"))
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    return qs


def get_clientes_bloqueados(*, company_id: Any) -> QuerySet:
    return _base_qs(company_id).filter(bloqueado=True).order_by("nome")


def get_clientes_inadimplentes(
    *, company_id: Any, saldo_minimo: Decimal = Decimal("0.01")
) -> QuerySet:
    return (
        _base_qs(company_id)
        .filter(saldo_devedor__gte=saldo_minimo)
        .order_by("-saldo_devedor", "nome")
    )
