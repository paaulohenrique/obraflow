from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from apps.boletos.services.extracao import (
    calcular_confianca,
    converter_linha_digitavel_para_codigo_barras,
    extrair_banco,
    extrair_beneficiario,
    extrair_codigo_barras,
    extrair_dados_boleto,
    extrair_documentos,
    extrair_linha_digitavel,
    extrair_valor,
    extrair_vencimento,
    normalizar_linha_digitavel,
    validar_linha_digitavel,
)
from apps.boletos.services.validators import validate_boleto_file

from .conftest import fake_line, jpg_file, pdf_file


@pytest.mark.django_db
def test_validate_boleto_file_accepts_pdf_and_image():
    pdf = validate_boleto_file(pdf_file())
    image = validate_boleto_file(jpg_file())

    assert pdf["tipo_arquivo"] == "PDF"
    assert pdf["preview_pages"] == 1
    assert len(pdf["sha256"]) == 64
    assert image["tipo_arquivo"] == "JPG"
    assert image["content_type"] == "image/jpeg"


def test_validate_boleto_file_rejects_invalid_cases():
    with pytest.raises(ValidationError):
        validate_boleto_file(SimpleUploadedFile("x.txt", b"abc", content_type="text/plain"))
    with pytest.raises(ValidationError):
        validate_boleto_file(SimpleUploadedFile("x.pdf", b"", content_type="application/pdf"))
    with pytest.raises(ValidationError):
        validate_boleto_file(SimpleUploadedFile("x.pdf", b"not-pdf", content_type="application/pdf"))
    with pytest.raises(ValidationError):
        validate_boleto_file(SimpleUploadedFile("x.jpg", b"%PDF-1.4", content_type="image/jpeg"))
    with pytest.raises(ValidationError):
        validate_boleto_file(SimpleUploadedFile("x.pdf", b"%PDF-1.4\n/Encrypt\n%%EOF", content_type="application/pdf"))


def test_extracao_linha_codigo_valor_vencimento_banco_docs():
    linha = fake_line()
    codigo = converter_linha_digitavel_para_codigo_barras(linha)
    texto = f"""
    Banco do Brasil 001
    Beneficiário: Energisa Teste
    CNPJ 45.997.418/0001-53
    Pagador 123.456.789-09
    Linha digitável: {linha}
    Valor do documento R$ 123,45
    Vencimento 30/06/2026
    """

    assert normalizar_linha_digitavel(linha) == linha
    assert validar_linha_digitavel(linha) is True
    assert extrair_linha_digitavel(texto) == linha
    assert extrair_codigo_barras(texto) == codigo
    assert extrair_valor(texto, codigo) == Decimal("123.45")
    assert extrair_vencimento(texto).isoformat() == "2026-06-30"
    assert extrair_banco(texto, codigo) == ("001", "Banco do Brasil")
    assert extrair_beneficiario(texto) == "Energisa Teste"
    docs = extrair_documentos(texto)
    assert docs["documento_beneficiario"] == "45997418000153"
    assert docs["documento_pagador"] == "12345678909"


def test_extrair_dados_and_confidence_never_reaches_100():
    linha = fake_line()
    dados = extrair_dados_boleto(f"Beneficiário: Energisa\nCNPJ 45.997.418/0001-53\n{linha}")
    score, fields = calcular_confianca(dados.campos)

    assert dados.campos["linha_digitavel"] == linha
    assert dados.campos["codigo_barras"]
    assert dados.confianca <= Decimal("95.00")
    assert score == dados.confianca
    assert fields["linha_digitavel"] > 0
