from rest_framework import serializers

from apps.core.serializers import BaseModelSerializer
from .models import Empresa


class EmpresaListSerializer(BaseModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id",
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "telefone",
            "email",
            "plano",
            "limite_usuarios",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EmpresaDetailSerializer(BaseModelSerializer):
    total_usuarios = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            "id",
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "telefone",
            "email",
            "plano",
            "limite_usuarios",
            "total_usuarios",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_total_usuarios(self, obj) -> int:
        return obj.usuarios.filter(is_active=True, deleted_at__isnull=True).count()


class EmpresaCreateSerializer(serializers.ModelSerializer):
    cnpj = serializers.CharField(max_length=18)

    class Meta:
        model = Empresa
        fields = [
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "telefone",
            "email",
            "plano",
            "limite_usuarios",
        ]


class EmpresaUpdateSerializer(serializers.ModelSerializer):
    cnpj = serializers.CharField(max_length=18, required=False)

    class Meta:
        model = Empresa
        fields = [
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "telefone",
            "email",
            "plano",
            "limite_usuarios",
        ]
