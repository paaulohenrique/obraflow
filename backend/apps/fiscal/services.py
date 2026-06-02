from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.empresas.validators import clean_cnpj

from .models import ConfiguracaoFiscalEmpresa


def _snapshot(config: ConfiguracaoFiscalEmpresa) -> dict[str, Any]:
    return {
        "id": str(config.pk),
        "company_id": str(config.company_id),
        "cnpj": config.cnpj,
        "razao_social": config.razao_social,
        "nome_fantasia": config.nome_fantasia,
        "inscricao_estadual": config.inscricao_estadual,
        "inscricao_municipal": config.inscricao_municipal,
        "regime_tributario": config.regime_tributario,
        "crt": config.crt,
        "cnae": config.cnae,
        "uf": config.uf,
        "municipio": config.municipio,
        "municipio_ibge": config.municipio_ibge,
        "logradouro": config.logradouro,
        "numero": config.numero,
        "complemento": config.complemento,
        "bairro": config.bairro,
        "cep": config.cep,
        "ambiente_fiscal": config.ambiente_fiscal,
        "provider_fiscal": config.provider_fiscal,
        "provider_company_id": config.provider_company_id,
        "ativo": config.ativo,
        "cadastro_fiscal_pronto": config.cadastro_fiscal_pronto,
        "is_active": config.is_active,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def get_or_create_configuracao_fiscal(*, user) -> ConfiguracaoFiscalEmpresa:
    require_company(user)
    config, _ = ConfiguracaoFiscalEmpresa.objects.get_or_create(
        company=user.company,
        defaults={
            "cnpj": clean_cnpj(user.company.cnpj or ""),
            "razao_social": user.company.razao_social,
            "nome_fantasia": user.company.nome_fantasia,
        },
    )
    return config


@transaction.atomic
def update_configuracao_fiscal(
    *,
    user,
    data: dict[str, Any],
    request=None,
) -> ConfiguracaoFiscalEmpresa:
    config = get_or_create_configuracao_fiscal(user=user)
    before = _snapshot(config)

    updatable = {
        "cnpj",
        "razao_social",
        "nome_fantasia",
        "inscricao_estadual",
        "inscricao_municipal",
        "regime_tributario",
        "crt",
        "cnae",
        "uf",
        "municipio",
        "municipio_ibge",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
        "ambiente_fiscal",
        "provider_fiscal",
        "provider_company_id",
        "ativo",
    }
    for field, value in data.items():
        if field in updatable:
            setattr(config, field, value)

    _full_clean_or_400(config)
    config.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=config,
        before=before,
        after=_snapshot(config),
        request=request,
    )
    return config
