import logging
from decimal import Decimal
from typing import Any

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.clientes.models import Cliente
from apps.clientes.validators import validate_documento, clean_telefone

logger = logging.getLogger("apps.clientes")


def _snapshot(cliente: Cliente) -> dict[str, Any]:
    return {
        "id": str(cliente.pk),
        "nome": cliente.nome,
        "tipo_pessoa": cliente.tipo_pessoa,
        "cpf_cnpj": cliente.cpf_cnpj,
        "telefone": cliente.telefone,
        "whatsapp": cliente.whatsapp,
        "email": cliente.email,
        "limite_credito": str(cliente.limite_credito),
        "saldo_devedor": str(cliente.saldo_devedor),
        "bloqueado": cliente.bloqueado,
        "is_active": cliente.is_active,
    }


def _check_documento_unique(
    tipo_pessoa: str,
    cpf_cnpj: str,
    company_id: Any,
    exclude_pk=None,
) -> None:
    qs = Cliente.objects.filter(
        company_id=company_id,
        cpf_cnpj=cpf_cnpj,
        deleted_at__isnull=True,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        label = "CPF" if tipo_pessoa == Cliente.TIPO_PF else "CNPJ"
        raise ValidationError({
            "cpf_cnpj": f"{label} já cadastrado para outro cliente nesta empresa."
        })


@transaction.atomic
def create_cliente(
    *,
    user,
    data: dict[str, Any],
    request=None,
) -> Cliente:
    require_company(user)

    tipo_pessoa = data.get("tipo_pessoa", Cliente.TIPO_PF)
    raw_doc = data.get("cpf_cnpj", "")

    valid, cleaned_doc = validate_documento(tipo_pessoa, raw_doc)
    if not valid:
        label = "CPF" if tipo_pessoa == Cliente.TIPO_PF else "CNPJ"
        raise ValidationError({"cpf_cnpj": f"{label} inválido."})

    company = getattr(user, "company", None)
    company_id = getattr(user, "company_id", None)
    _check_documento_unique(tipo_pessoa, cleaned_doc, company_id)

    cliente = Cliente(
        company=company,
        nome=data["nome"],
        tipo_pessoa=tipo_pessoa,
        cpf_cnpj=cleaned_doc,
        telefone=clean_telefone(data.get("telefone", "")),
        whatsapp=clean_telefone(data.get("whatsapp", "")),
        email=data.get("email", ""),
        cep=data.get("cep", ""),
        rua=data.get("rua", ""),
        numero=data.get("numero", ""),
        bairro=data.get("bairro", ""),
        cidade=data.get("cidade", ""),
        estado=data.get("estado", ""),
        complemento=data.get("complemento", ""),
        observacao=data.get("observacao", ""),
        limite_credito=data.get("limite_credito", Decimal("0.00")),
        saldo_devedor=Decimal("0.00"),
        bloqueado=False,
        data_ultimo_pagamento=data.get("data_ultimo_pagamento"),
    )
    cliente.full_clean()
    cliente.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=cliente,
        after=_snapshot(cliente),
        request=request,
    )

    logger.info("Cliente criado: %s (empresa=%s)", cliente.pk, company_id)
    return cliente


@transaction.atomic
def update_cliente(
    *,
    user,
    cliente: Cliente,
    data: dict[str, Any],
    request=None,
) -> Cliente:
    require_company(user)
    before = _snapshot(cliente)
    company_id = getattr(user, "company_id", None)

    # Handle documento change
    if "cpf_cnpj" in data or "tipo_pessoa" in data:
        tipo_pessoa = data.get("tipo_pessoa", cliente.tipo_pessoa)
        raw_doc = data.get("cpf_cnpj", cliente.cpf_cnpj)
        valid, cleaned_doc = validate_documento(tipo_pessoa, raw_doc)
        if not valid:
            label = "CPF" if tipo_pessoa == Cliente.TIPO_PF else "CNPJ"
            raise ValidationError({"cpf_cnpj": f"{label} inválido."})
        _check_documento_unique(tipo_pessoa, cleaned_doc, company_id, exclude_pk=cliente.pk)
        data = {**data, "cpf_cnpj": cleaned_doc, "tipo_pessoa": tipo_pessoa}

    if "telefone" in data:
        data["telefone"] = clean_telefone(data["telefone"])
    if "whatsapp" in data:
        data["whatsapp"] = clean_telefone(data["whatsapp"])

    updatable = {
        "nome", "tipo_pessoa", "cpf_cnpj", "telefone", "whatsapp", "email",
        "cep", "rua", "numero", "bairro", "cidade", "estado", "complemento",
        "observacao", "limite_credito", "data_ultimo_pagamento",
    }
    for field, value in data.items():
        if field in updatable:
            setattr(cliente, field, value)

    cliente.full_clean()
    cliente.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=before,
        after=_snapshot(cliente),
        request=request,
    )
    return cliente


@transaction.atomic
def bloquear_cliente(*, user, cliente: Cliente, request=None) -> Cliente:
    require_company(user)
    if cliente.bloqueado:
        raise ValidationError({"bloqueado": "Cliente já está bloqueado."})
    before = _snapshot(cliente)
    cliente.bloqueado = True
    cliente.save(update_fields=["bloqueado", "updated_at"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=before,
        after=_snapshot(cliente),
        request=request,
    )
    return cliente


@transaction.atomic
def desbloquear_cliente(*, user, cliente: Cliente, request=None) -> Cliente:
    require_company(user)
    if not cliente.bloqueado:
        raise ValidationError({"bloqueado": "Cliente não está bloqueado."})
    before = _snapshot(cliente)
    cliente.bloqueado = False
    cliente.save(update_fields=["bloqueado", "updated_at"])
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=before,
        after=_snapshot(cliente),
        request=request,
    )
    return cliente


@transaction.atomic
def soft_delete_cliente(*, user, cliente: Cliente, request=None) -> None:
    require_company(user)
    before = _snapshot(cliente)
    cliente.soft_delete()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=cliente,
        before=before,
        request=request,
    )
