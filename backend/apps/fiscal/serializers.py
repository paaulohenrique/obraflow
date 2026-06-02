from rest_framework import serializers

from apps.core.serializers import BaseModelSerializer
from apps.empresas.validators import clean_cnpj, is_valid_cnpj

from .models import ConfiguracaoFiscalEmpresa
from .validators import validate_cep, validate_cnae, validate_municipio_ibge


class ConfiguracaoFiscalEmpresaSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    cadastro_fiscal_pronto = serializers.BooleanField(read_only=True)

    class Meta:
        model = ConfiguracaoFiscalEmpresa
        fields = [
            "id",
            "company_id",
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
            "cadastro_fiscal_pronto",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "cadastro_fiscal_pronto",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        forbidden_sensitive = {"certificado_a1", "certificado_senha", "provider_token"}
        if forbidden_sensitive & set(getattr(self, "initial_data", {}) or {}):
            raise serializers.ValidationError({
                "detail": "Credenciais fiscais sensíveis ainda não são aceitas por esta API."
            })
        return attrs

    def validate_cnpj(self, value):
        cleaned = clean_cnpj(value)
        if cleaned and not is_valid_cnpj(cleaned):
            raise serializers.ValidationError("CNPJ inválido.")
        return cleaned

    def validate_cnae(self, value):
        return validate_cnae(value)

    def validate_municipio_ibge(self, value):
        return validate_municipio_ibge(value)

    def validate_cep(self, value):
        return validate_cep(value)
