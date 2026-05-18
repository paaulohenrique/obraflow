import uuid
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound

from .models import Empresa


def get_empresa_by_id(*, empresa_id: Any) -> Empresa:
    try:
        return Empresa.objects.get(pk=empresa_id, deleted_at__isnull=True)
    except (Empresa.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Empresa não encontrada.")


def get_empresas_ativas() -> QuerySet:
    return Empresa.objects.filter(deleted_at__isnull=True, is_active=True).order_by("razao_social")


def get_all_empresas() -> QuerySet:
    return Empresa.objects.filter(deleted_at__isnull=True).order_by("razao_social")
