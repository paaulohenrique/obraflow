import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any


BANCOS = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "104": "Caixa Econômica Federal",
    "237": "Bradesco",
    "341": "Itaú",
    "756": "Sicoob",
}


@dataclass(frozen=True)
class DadosExtraidos:
    campos: dict[str, Any]
    confiancas: dict[str, int]
    confianca: Decimal


def only_digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def normalizar_linha_digitavel(linha: str) -> str:
    digits = only_digits(linha)
    return digits if len(digits) in (47, 48) else ""


def _mod10_digit(numbers: str) -> int:
    total = 0
    multiplier = 2
    for char in reversed(numbers):
        value = int(char) * multiplier
        total += value if value < 10 else (value // 10) + (value % 10)
        multiplier = 1 if multiplier == 2 else 2
    remainder = total % 10
    return 0 if remainder == 0 else 10 - remainder


def validar_linha_digitavel(linha: str) -> bool:
    linha = normalizar_linha_digitavel(linha)
    if not linha:
        return False
    if len(linha) == 48:
        return True
    return (
        _mod10_digit(linha[0:9]) == int(linha[9])
        and _mod10_digit(linha[10:20]) == int(linha[20])
        and _mod10_digit(linha[21:31]) == int(linha[31])
    )


def converter_linha_digitavel_para_codigo_barras(linha: str) -> str:
    linha = normalizar_linha_digitavel(linha)
    if not linha:
        return ""
    if len(linha) == 48:
        return linha[:44]
    return linha[0:4] + linha[32] + linha[33:47] + linha[4:9] + linha[10:20] + linha[21:31]


def extrair_linha_digitavel(texto: str) -> str:
    candidates = re.findall(r"(?:\d[ .\-]?){47,54}", texto or "")
    for candidate in candidates:
        linha = normalizar_linha_digitavel(candidate)
        if linha and validar_linha_digitavel(linha):
            return linha
    for candidate in candidates:
        linha = normalizar_linha_digitavel(candidate)
        if linha:
            return linha
    return ""


def extrair_codigo_barras(texto: str) -> str:
    for candidate in re.findall(r"\b\d{44}\b", texto or ""):
        return candidate
    linha = extrair_linha_digitavel(texto)
    return converter_linha_digitavel_para_codigo_barras(linha)


def _decimal_from_money(value: str) -> Decimal | None:
    value = (value or "").strip().replace(".", "").replace(",", ".")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed > 0 else None


def _valor_from_barcode(codigo_barras: str) -> Decimal | None:
    if not codigo_barras or len(codigo_barras) != 44 or not codigo_barras.isdigit():
        return None
    raw = codigo_barras[9:19]
    try:
        value = Decimal(raw) / Decimal("100")
    except InvalidOperation:
        return None
    return value if value > 0 else None


def extrair_valor(texto: str, codigo_barras: str = "") -> Decimal | None:
    if value := _valor_from_barcode(codigo_barras):
        return value
    patterns = [
        r"(?:valor(?:\s+do\s+documento)?|total|documento)\D{0,20}(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, texto or "", flags=re.IGNORECASE):
            if value := _decimal_from_money(match):
                return value
    return None


def _vencimento_from_barcode(codigo_barras: str) -> date | None:
    if not codigo_barras or len(codigo_barras) != 44 or not codigo_barras.isdigit():
        return None
    factor = int(codigo_barras[5:9])
    if factor == 0:
        return None
    base = date(1997, 10, 7)
    vencimento = base + timedelta(days=factor)
    if vencimento > date(2025, 2, 21):
        return vencimento
    if factor >= 1000:
        return date(2025, 2, 22) + timedelta(days=factor - 1000)
    return vencimento


def _parse_date(raw: str) -> date | None:
    raw = raw.replace("-", "/").strip()
    parts = raw.split("/")
    if len(parts) != 3:
        return None
    day, month, year = parts
    if len(year) == 2:
        year = "20" + year
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def extrair_vencimento(texto: str, codigo_barras: str = "") -> date | None:
    if value := _vencimento_from_barcode(codigo_barras):
        return value
    patterns = [
        r"(?:vencimento|vcto|vence)\D{0,20}(\d{2}[/-]\d{2}[/-]\d{2,4})",
        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, texto or "", flags=re.IGNORECASE):
            if parsed := _parse_date(match):
                return parsed
    return None


def extrair_banco(texto: str, codigo_barras: str = "") -> tuple[str, str]:
    if codigo_barras and len(codigo_barras) >= 3 and codigo_barras[:3].isdigit():
        codigo = codigo_barras[:3]
        return codigo, BANCOS.get(codigo, "")
    lowered = (texto or "").lower()
    for codigo, nome in BANCOS.items():
        if nome.lower().split()[0] in lowered or codigo in lowered:
            return codigo, nome
    return "", ""


def extrair_documentos(texto: str) -> dict[str, str]:
    docs = re.findall(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", texto or "")
    cleaned = [only_digits(doc) for doc in docs]
    return {
        "documento_beneficiario": cleaned[0] if cleaned else "",
        "documento_pagador": cleaned[1] if len(cleaned) > 1 else "",
    }


def extrair_beneficiario(texto: str) -> str:
    lines = [line.strip(" :-\t") for line in (texto or "").splitlines() if line.strip()]
    keywords = ("beneficiário", "beneficiario", "cedente", "favorecido")
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            tail = re.sub(r".*?(benefici[aá]rio|cedente|favorecido)\s*:?\s*", "", line, flags=re.IGNORECASE)
            tail = tail.strip(" :-\t")
            if tail and len(tail) > 2:
                return tail[:300]
            if index + 1 < len(lines):
                return lines[index + 1][:300]
    return ""


def calcular_confianca(dados_extraidos: dict[str, Any]) -> tuple[Decimal, dict[str, int]]:
    fields = {
        "linha_digitavel": 30,
        "codigo_barras": 25,
        "valor": 15,
        "vencimento": 15,
        "banco_codigo": 5,
        "fornecedor_nome": 5,
        "documento_beneficiario": 5,
    }
    score = 0
    per_field = {}
    for field, weight in fields.items():
        present = bool(dados_extraidos.get(field))
        per_field[field] = weight if present else 0
        score += weight if present else 0
    if dados_extraidos.get("linha_digitavel") and not validar_linha_digitavel(dados_extraidos["linha_digitavel"]):
        score -= 20
        per_field["linha_digitavel"] = 10
    score = max(0, min(score, 95))
    return Decimal(score).quantize(Decimal("0.01")), per_field


def extrair_dados_boleto(texto: str) -> DadosExtraidos:
    linha = extrair_linha_digitavel(texto)
    codigo = extrair_codigo_barras(texto)
    banco_codigo, banco_nome = extrair_banco(texto, codigo)
    docs = extrair_documentos(texto)
    campos = {
        "linha_digitavel": linha,
        "codigo_barras": codigo,
        "valor": extrair_valor(texto, codigo),
        "vencimento": extrair_vencimento(texto, codigo),
        "banco_codigo": banco_codigo,
        "banco_nome": banco_nome,
        "fornecedor_nome": extrair_beneficiario(texto),
        **docs,
    }
    confianca, confiancas = calcular_confianca(campos)
    return DadosExtraidos(campos=campos, confiancas=confiancas, confianca=confianca)
