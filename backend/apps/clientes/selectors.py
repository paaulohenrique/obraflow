from decimal import Decimal
from typing import Any
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound

from .models import Cliente


def _base_qs(company_id: Any) -> QuerySet:
    """Active (non-deleted) clients scoped to the tenant."""
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


def search_clientes(*, company_id: Any, filters: dict | None = None) -> QuerySet:
    qs = _base_qs(company_id)
    if not filters:
        return qs.order_by("nome")

    if q := filters.get("search"):
        from django.db.models import Q
        qs = qs.filter(
            Q(nome__icontains=q)
            | Q(cpf_cnpj__icontains=q)
            | Q(telefone__icontains=q)
            | Q(whatsapp__icontains=q)
            | Q(email__icontains=q)
        )

    if (bloqueado := filters.get("bloqueado")) is not None:
        qs = qs.filter(bloqueado=bloqueado)

    if tipo := filters.get("tipo_pessoa"):
        qs = qs.filter(tipo_pessoa=tipo)

    if cidade := filters.get("cidade"):
        qs = qs.filter(cidade__icontains=cidade)

    if estado := filters.get("estado"):
        qs = qs.filter(estado=estado.upper())

    if (saldo_gt := filters.get("saldo_devedor__gt")) is not None:
        qs = qs.filter(saldo_devedor__gt=Decimal(str(saldo_gt)))

    if (is_active := filters.get("is_active")) is not None:
        qs = qs.filter(is_active=is_active)

    return qs.order_by("nome")


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
