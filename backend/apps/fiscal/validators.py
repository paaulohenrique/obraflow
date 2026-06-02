import re

from django.core.exceptions import ValidationError


def only_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def validate_ncm(value: str | None) -> str:
    cleaned = only_digits(value)
    if cleaned and len(cleaned) != 8:
        raise ValidationError("NCM deve conter 8 dígitos numéricos.")
    return cleaned


def validate_cfop(value: str | None) -> str:
    cleaned = only_digits(value)
    if cleaned and len(cleaned) != 4:
        raise ValidationError("CFOP deve conter 4 dígitos numéricos.")
    return cleaned


def validate_cest(value: str | None) -> str:
    cleaned = only_digits(value)
    if cleaned and len(cleaned) != 7:
        raise ValidationError("CEST deve conter 7 dígitos numéricos.")
    return cleaned


def validate_municipio_ibge(value: str | None) -> str:
    cleaned = only_digits(value)
    if cleaned and len(cleaned) != 7:
        raise ValidationError("Código IBGE do município deve conter 7 dígitos numéricos.")
    return cleaned


def validate_cep(value: str | None) -> str:
    cleaned = only_digits(value)
    if cleaned and len(cleaned) != 8:
        raise ValidationError("CEP deve conter 8 dígitos numéricos.")
    return cleaned


def validate_cnae(value: str | None) -> str:
    cleaned = only_digits(value)
    if cleaned and len(cleaned) != 7:
        raise ValidationError("CNAE deve conter 7 dígitos numéricos.")
    return cleaned


def validate_ie_required(*, indicador_ie: str, inscricao_estadual: str | None) -> None:
    if indicador_ie == "CONTRIBUINTE" and not (inscricao_estadual or "").strip():
        raise ValidationError({"inscricao_estadual": "Inscrição estadual é obrigatória para contribuinte ICMS."})
