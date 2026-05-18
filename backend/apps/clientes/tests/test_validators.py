import pytest
from apps.clientes.validators import (
    is_valid_cpf,
    is_valid_cnpj,
    clean_documento,
    clean_telefone,
    validate_documento,
)


class TestCPFValidator:
    def test_valid_cpf(self):
        assert is_valid_cpf("52998224725") is True

    def test_valid_cpf_with_mask(self):
        assert is_valid_cpf("529.982.247-25") is True

    def test_valid_cpf_2(self):
        assert is_valid_cpf("11144477735") is True

    def test_valid_cpf_3(self):
        assert is_valid_cpf("12345678909") is True

    def test_invalid_cpf_wrong_digit(self):
        assert is_valid_cpf("52998224726") is False

    def test_invalid_cpf_too_short(self):
        assert is_valid_cpf("1234567890") is False

    def test_invalid_cpf_too_long(self):
        assert is_valid_cpf("123456789012") is False

    def test_invalid_cpf_all_same(self):
        for d in "0123456789":
            assert is_valid_cpf(d * 11) is False

    def test_invalid_cpf_empty(self):
        assert is_valid_cpf("") is False

    def test_invalid_cpf_letters(self):
        assert is_valid_cpf("abc.def.ghi-jk") is False


class TestCNPJValidator:
    def test_valid_cnpj(self):
        assert is_valid_cnpj("11222333000181") is True

    def test_valid_cnpj_with_mask(self):
        assert is_valid_cnpj("11.222.333/0001-81") is True

    def test_valid_cnpj_2(self):
        assert is_valid_cnpj("11444777000161") is True

    def test_invalid_cnpj_wrong_digit(self):
        assert is_valid_cnpj("11222333000182") is False

    def test_invalid_cnpj_too_short(self):
        assert is_valid_cnpj("1122233300018") is False

    def test_invalid_cnpj_all_same(self):
        for d in "0123456789":
            assert is_valid_cnpj(d * 14) is False

    def test_invalid_cnpj_empty(self):
        assert is_valid_cnpj("") is False


class TestCleanDocumento:
    def test_removes_cpf_mask(self):
        assert clean_documento("529.982.247-25") == "52998224725"

    def test_removes_cnpj_mask(self):
        assert clean_documento("11.222.333/0001-81") == "11222333000181"

    def test_already_clean(self):
        assert clean_documento("52998224725") == "52998224725"


class TestCleanTelefone:
    def test_removes_mask(self):
        assert clean_telefone("(11) 99999-0001") == "11999990001"

    def test_already_clean(self):
        assert clean_telefone("11999990001") == "11999990001"

    def test_empty(self):
        assert clean_telefone("") == ""


class TestValidateDocumento:
    def test_valid_pf(self):
        ok, cleaned = validate_documento("PF", "529.982.247-25")
        assert ok is True
        assert cleaned == "52998224725"

    def test_invalid_pf(self):
        ok, cleaned = validate_documento("PF", "000.000.000-00")
        assert ok is False

    def test_valid_pj(self):
        ok, cleaned = validate_documento("PJ", "11.222.333/0001-81")
        assert ok is True
        assert cleaned == "11222333000181"

    def test_invalid_pj(self):
        ok, _ = validate_documento("PJ", "00.000.000/0000-00")
        assert ok is False

    def test_cpf_as_pj_invalid(self):
        ok, _ = validate_documento("PJ", "529.982.247-25")
        assert ok is False

    def test_cnpj_as_pf_invalid(self):
        ok, _ = validate_documento("PF", "11.222.333/0001-81")
        assert ok is False
