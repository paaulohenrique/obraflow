from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import BaseModelSerializer
from .models import Cliente
from .validators import validate_documento


class ClienteListSerializer(BaseModelSerializer):
    """Lightweight serializer for list views — avoids heavy fields."""

    credito_disponivel = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    inadimplente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "nome",
            "tipo_pessoa",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "email",
            "cidade",
            "estado",
            "limite_credito",
            "saldo_devedor",
            "credito_disponivel",
            "inadimplente",
            "bloqueado",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClienteDetailSerializer(BaseModelSerializer):
    """Full serializer for retrieve — includes address and financial fields."""

    credito_disponivel = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    inadimplente = serializers.BooleanField(read_only=True)
    # company_id is the Django FK column — UUID of the related Empresa
    company_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "nome",
            "tipo_pessoa",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "email",
            "cep",
            "rua",
            "numero",
            "bairro",
            "cidade",
            "estado",
            "complemento",
            "observacao",
            "limite_credito",
            "saldo_devedor",
            "credito_disponivel",
            "inadimplente",
            "bloqueado",
            "data_ultimo_pagamento",
            "is_active",
            "company_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClienteCreateSerializer(serializers.ModelSerializer):
    # Accept masked input (max 18 chars for CNPJ XX.XXX.XXX/XXXX-XX)
    cpf_cnpj = serializers.CharField(max_length=18)

    class Meta:
        model = Cliente
        fields = [
            "nome",
            "tipo_pessoa",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "email",
            "cep",
            "rua",
            "numero",
            "bairro",
            "cidade",
            "estado",
            "complemento",
            "observacao",
            "limite_credito",
            "data_ultimo_pagamento",
        ]

    def validate(self, attrs):
        tipo_pessoa = attrs.get("tipo_pessoa", Cliente.TIPO_PF)
        cpf_cnpj = attrs.get("cpf_cnpj", "")
        if cpf_cnpj:
            valid, cleaned = validate_documento(tipo_pessoa, cpf_cnpj)
            if not valid:
                label = "CPF" if tipo_pessoa == Cliente.TIPO_PF else "CNPJ"
                raise ValidationError({"cpf_cnpj": f"{label} inválido."})
        return attrs


class ClienteUpdateSerializer(serializers.ModelSerializer):
    cpf_cnpj = serializers.CharField(max_length=18, required=False)

    class Meta:
        model = Cliente
        fields = [
            "nome",
            "tipo_pessoa",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "email",
            "cep",
            "rua",
            "numero",
            "bairro",
            "cidade",
            "estado",
            "complemento",
            "observacao",
            "limite_credito",
            "data_ultimo_pagamento",
        ]

    def validate(self, attrs):
        tipo_pessoa = attrs.get("tipo_pessoa") or (
            self.instance.tipo_pessoa if self.instance else Cliente.TIPO_PF
        )
        cpf_cnpj = attrs.get("cpf_cnpj")
        if cpf_cnpj:
            valid, cleaned = validate_documento(tipo_pessoa, cpf_cnpj)
            if not valid:
                label = "CPF" if tipo_pessoa == Cliente.TIPO_PF else "CNPJ"
                raise ValidationError({"cpf_cnpj": f"{label} inválido."})
        return attrs
