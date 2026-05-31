"""Testes do parser XML NF-e."""
import pytest

from apps.notas_entrada.services.validators import MAX_XML_SIZE, validate_xml_file
from apps.notas_entrada.services.xml_parser import parse_nfe_xml
from rest_framework.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from .conftest import FIXTURES_DIR, xml_bytes


class TestXMLParser:
    def test_parse_nfe_valida(self):
        conteudo = xml_bytes("nfe_valida.xml")
        payload = parse_nfe_xml(conteudo)

        assert payload.numero == "123"
        assert payload.serie == "1"
        assert payload.modelo == "55"
        assert payload.data_emissao == "2026-05-30"
        assert payload.fornecedor_cnpj == "12345678000195"
        assert payload.fornecedor_nome == "Distribuidora Teste Ltda"
        assert payload.destinatario_cnpj == "11222333000181"
        assert len(payload.itens) == 3

    def test_parse_valores_fiscais(self):
        conteudo = xml_bytes("nfe_valida.xml")
        payload = parse_nfe_xml(conteudo)

        from decimal import Decimal
        assert payload.valor_total == Decimal("5325.00")
        assert payload.valor_produtos == Decimal("5050.00")
        assert payload.valor_frete == Decimal("200.00")
        assert payload.valor_desconto == Decimal("50.00")
        assert payload.valor_icms == Decimal("606.00")
        assert payload.valor_ipi == Decimal("125.00")

    def test_parse_itens_detalhados(self):
        conteudo = xml_bytes("nfe_valida.xml")
        payload = parse_nfe_xml(conteudo)

        from decimal import Decimal
        item1 = payload.itens[0]
        assert item1.ordem == 1
        assert item1.codigo_fornecedor == "001"
        assert item1.codigo_barras == "7891000315507"
        assert item1.descricao_original == "CIMENTO CP-II 50KG"
        assert item1.ncm == "25232900"
        assert item1.cfop == "1102"
        assert item1.unidade == "SC"
        assert item1.quantidade == Decimal("100.000")
        assert item1.valor_unitario == Decimal("25.00")
        assert item1.valor_total_item == Decimal("2500.00")
        assert item1.valor_icms_item == Decimal("300.00")
        assert item1.valor_ipi_item == Decimal("125.00")

    def test_parse_item_sem_gtin(self):
        conteudo = xml_bytes("nfe_valida.xml")
        payload = parse_nfe_xml(conteudo)

        item2 = payload.itens[1]
        assert item2.codigo_barras == ""  # SEM GTIN convertido para vazio

    def test_parse_xml_sem_namespace(self):
        conteudo = xml_bytes("nfe_sem_namespace.xml")
        payload = parse_nfe_xml(conteudo)

        assert payload.numero == "999"
        assert payload.fornecedor_cnpj == "12345678000195"
        assert len(payload.itens) == 1
        assert payload.itens[0].codigo_barras == "7891000000001"

    def test_parse_xml_malformado(self):
        conteudo = b"<xml>malformado"
        with pytest.raises(ValidationError) as exc_info:
            parse_nfe_xml(conteudo)
        assert "arquivo" in exc_info.value.detail

    def test_parse_xml_sem_nfe(self):
        conteudo = b"<root><outro>elemento</outro></root>"
        with pytest.raises(ValidationError) as exc_info:
            parse_nfe_xml(conteudo)
        assert "arquivo" in exc_info.value.detail

    def test_parse_xml_sem_itens(self):
        conteudo = b"""<?xml version="1.0"?>
        <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
          <NFe xmlns="http://www.portalfiscal.inf.br/nfe">
            <infNFe Id="NFe000" versao="4.00">
              <ide><mod>55</mod><serie>1</serie><nNF>1</nNF><dhEmi>2026-01-01T00:00:00</dhEmi></ide>
              <emit><CNPJ>12345678000195</CNPJ><xNome>Emit</xNome></emit>
              <total><ICMSTot><vNF>100.00</vNF><vProd>100.00</vProd><vFrete>0.00</vFrete><vDesc>0.00</vDesc><vICMS>0.00</vICMS><vIPI>0.00</vIPI></ICMSTot></total>
            </infNFe>
          </NFe>
        </nfeProc>"""
        with pytest.raises(ValidationError) as exc_info:
            parse_nfe_xml(conteudo)
        assert "arquivo" in exc_info.value.detail

    def test_parse_xxe_bloqueado(self):
        xxe_payload = b"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
        <root>&xxe;</root>"""
        with pytest.raises((ValidationError, Exception)):
            parse_nfe_xml(xxe_payload)

    def test_parse_billion_laughs_bloqueado(self):
        billion_laughs = b"""<?xml version="1.0"?>
        <!DOCTYPE lolz [
          <!ENTITY lol "lol">
          <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
          <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        ]>
        <root>&lol3;</root>"""
        with pytest.raises((ValidationError, Exception)):
            parse_nfe_xml(billion_laughs)


class TestValidateXMLFile:
    def test_arquivo_valido(self):
        conteudo = xml_bytes("nfe_valida.xml")
        arquivo = SimpleUploadedFile("nfe.xml", conteudo, content_type="text/xml")
        meta = validate_xml_file(arquivo)
        assert "sha256" in meta
        assert len(meta["sha256"]) == 64
        assert meta["tamanho_bytes"] > 0

    def test_extensao_invalida(self):
        arquivo = SimpleUploadedFile("nfe.pdf", b"conteudo", content_type="application/pdf")
        with pytest.raises(ValidationError) as exc_info:
            validate_xml_file(arquivo)
        assert "arquivo" in exc_info.value.detail

    def test_arquivo_vazio(self):
        arquivo = SimpleUploadedFile("nfe.xml", b"", content_type="text/xml")
        with pytest.raises(ValidationError) as exc_info:
            validate_xml_file(arquivo)
        assert "arquivo" in exc_info.value.detail

    def test_arquivo_grande_demais(self):
        conteudo = b"x" * (MAX_XML_SIZE + 1)
        arquivo = SimpleUploadedFile("nfe.xml", conteudo, content_type="text/xml")
        with pytest.raises(ValidationError) as exc_info:
            validate_xml_file(arquivo)
        assert "arquivo" in exc_info.value.detail

    def test_mime_invalido_bloqueado(self):
        arquivo = SimpleUploadedFile("nfe.xml", b"<xml/>", content_type="application/octet-stream")
        with pytest.raises(ValidationError) as exc_info:
            validate_xml_file(arquivo)
        assert "arquivo" in exc_info.value.detail

    def test_sha256_calculado_corretamente(self):
        import hashlib
        conteudo = b"<xml>teste</xml>"
        arquivo = SimpleUploadedFile("nfe.xml", conteudo, content_type="text/xml")
        meta = validate_xml_file(arquivo)
        esperado = hashlib.sha256(conteudo).hexdigest()
        assert meta["sha256"] == esperado
