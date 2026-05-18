import re
from typing import Literal


def _clean_doc(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_valid_cpf(cpf: str) -> bool:
    cpf = _clean_doc(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    # First check digit
    total = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (total * 10) % 11
    if d1 >= 10:
        d1 = 0
    if d1 != int(cpf[9]):
        return False
    # Second check digit
    total = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (total * 10) % 11
    if d2 >= 10:
        d2 = 0
    return d2 == int(cpf[10])


def is_valid_cnpj(cnpj: str) -> bool:
    cnpj = _clean_doc(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    # First check digit
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * w1[i] for i in range(12))
    d1 = 11 - (total % 11)
    if d1 >= 10:
        d1 = 0
    if d1 != int(cnpj[12]):
        return False
    # Second check digit
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * w2[i] for i in range(13))
    d2 = 11 - (total % 11)
    if d2 >= 10:
        d2 = 0
    return d2 == int(cnpj[13])


def clean_documento(value: str) -> str:
    """Strip non-numeric characters for storage."""
    return _clean_doc(value)


def clean_telefone(value: str) -> str:
    """Strip non-numeric characters from phone number."""
    return re.sub(r"\D", "", value) if value else ""


def validate_documento(
    tipo_pessoa: Literal["PF", "PJ"],
    cpf_cnpj: str,
) -> tuple[bool, str]:
    """Return (is_valid, cleaned_value). Validates according to tipo_pessoa."""
    cleaned = clean_documento(cpf_cnpj)
    if tipo_pessoa == "PF":
        return is_valid_cpf(cleaned), cleaned
    return is_valid_cnpj(cleaned), cleaned
