import logging
from typing import Any

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from .models import Empresa
from .validators import clean_cnpj, is_valid_cnpj

logger = logging.getLogger("apps.empresas")


def _snapshot(empresa: Empresa) -> dict[str, Any]:
    return {
        "id": str(empresa.pk),
        "razao_social": empresa.razao_social,
        "cnpj": empresa.cnpj,
        "plano": empresa.plano,
        "is_active": empresa.is_active,
    }


def _validate_cnpj(raw: str) -> str:
    cleaned = clean_cnpj(raw)
    if not is_valid_cnpj(cleaned):
        raise ValidationError({"cnpj": "CNPJ inválido."})
    return cleaned


@transaction.atomic
def create_empresa(*, user, data: dict[str, Any], request=None) -> Empresa:
    cnpj = _validate_cnpj(data.get("cnpj", ""))

    if Empresa.objects.filter(cnpj=cnpj, deleted_at__isnull=True).exists():
        raise ValidationError({"cnpj": "CNPJ já cadastrado."})

    empresa = Empresa(
        razao_social=data["razao_social"],
        nome_fantasia=data.get("nome_fantasia", ""),
        cnpj=cnpj,
        telefone=data.get("telefone", ""),
        email=data.get("email", ""),
        plano=data.get("plano", Empresa.PLANO_BASICO),
        limite_usuarios=data.get("limite_usuarios", 10),
    )
    empresa.full_clean()
    empresa.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=empresa,
        after=_snapshot(empresa),
        request=request,
    )
    logger.info("Empresa criada: %s (%s)", empresa.pk, empresa.cnpj)
    return empresa


@transaction.atomic
def update_empresa(*, user, empresa: Empresa, data: dict[str, Any], request=None) -> Empresa:
    before = _snapshot(empresa)

    if "cnpj" in data:
        cnpj = _validate_cnpj(data["cnpj"])
        if Empresa.objects.filter(cnpj=cnpj, deleted_at__isnull=True).exclude(pk=empresa.pk).exists():
            raise ValidationError({"cnpj": "CNPJ já cadastrado."})
        data = {**data, "cnpj": cnpj}

    updatable = {"razao_social", "nome_fantasia", "cnpj", "telefone", "email", "plano", "limite_usuarios"}
    for field, value in data.items():
        if field in updatable:
            setattr(empresa, field, value)

    empresa.full_clean()
    empresa.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=empresa,
        before=before,
        after=_snapshot(empresa),
        request=request,
    )
    return empresa


@transaction.atomic
def soft_delete_empresa(*, user, empresa: Empresa, request=None) -> None:
    before = _snapshot(empresa)
    empresa.soft_delete()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=empresa,
        before=before,
        request=request,
    )
