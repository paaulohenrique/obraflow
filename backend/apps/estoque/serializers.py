from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import BaseModelSerializer
from apps.empresas.validators import clean_cnpj, is_valid_cnpj

from .models import (
    CategoriaProduto,
    Fornecedor,
    MovimentacaoEstoque,
    Produto,
    UnidadeMedida,
)


class RejectCompanyPayloadMixin:
    def run_validation(self, data=serializers.empty):
        if isinstance(data, dict) and {"company", "company_id"} & set(data):
            raise ValidationError({
                "company": "Empresa é definida pelo usuário autenticado e não deve ser enviada."
            })
        return super().run_validation(data)


class TenantScopedSerializerMixin(RejectCompanyPayloadMixin):
    tenant_scoped_fields: dict[str, type] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        company_id = getattr(getattr(request, "user", None), "company_id", None)
        if not company_id:
            return
        for field_name, model in self.tenant_scoped_fields.items():
            if field_name in self.fields:
                self.fields[field_name].queryset = model.objects.filter(
                    company_id=company_id,
                    deleted_at__isnull=True,
                )


class UnidadeSerializer(RejectCompanyPayloadMixin, BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = UnidadeMedida
        fields = [
            "id",
            "company_id",
            "nome",
            "sigla",
            "descricao",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "is_active", "created_at", "updated_at"]


class CategoriaSerializer(RejectCompanyPayloadMixin, BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = CategoriaProduto
        fields = [
            "id",
            "company_id",
            "nome",
            "descricao",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "is_active", "created_at", "updated_at"]


class FornecedorSerializer(RejectCompanyPayloadMixin, BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    cnpj = serializers.CharField(max_length=18)

    class Meta:
        model = Fornecedor
        fields = [
            "id",
            "company_id",
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "telefone",
            "email",
            "observacoes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "is_active", "created_at", "updated_at"]

    def validate_cnpj(self, value):
        cleaned = clean_cnpj(value)
        if not is_valid_cnpj(cleaned):
            raise ValidationError("CNPJ inválido.")
        return cleaned


class ProdutoListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    unidade_sigla = serializers.CharField(source="unidade.sigla", read_only=True)
    estoque_baixo = serializers.BooleanField(read_only=True)
    margem_percentual = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    def get_fornecedor_nome(self, obj) -> str | None:
        if not obj.fornecedor_principal:
            return None
        return str(obj.fornecedor_principal)

    class Meta:
        model = Produto
        fields = [
            "id",
            "company_id",
            "nome",
            "sku",
            "codigo_barras",
            "categoria",
            "categoria_nome",
            "fornecedor_principal",
            "fornecedor_nome",
            "unidade",
            "unidade_sigla",
            "preco_compra",
            "preco_venda",
            "custo_medio",
            "estoque_atual",
            "estoque_minimo",
            "estoque_baixo",
            "margem_percentual",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProdutoDetailSerializer(ProdutoListSerializer):
    class Meta(ProdutoListSerializer.Meta):
        fields = ProdutoListSerializer.Meta.fields + ["descricao"]
        read_only_fields = fields


class ProdutoCreateSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    tenant_scoped_fields = {
        "categoria": CategoriaProduto,
        "fornecedor_principal": Fornecedor,
        "unidade": UnidadeMedida,
    }

    class Meta:
        model = Produto
        fields = [
            "nome",
            "descricao",
            "sku",
            "codigo_barras",
            "categoria",
            "fornecedor_principal",
            "unidade",
            "preco_compra",
            "preco_venda",
            "custo_medio",
            "estoque_minimo",
        ]
        extra_kwargs = {
            "fornecedor_principal": {"required": False, "allow_null": True},
            "descricao": {"required": False, "allow_blank": True},
            "sku": {"required": False, "allow_blank": True},
            "codigo_barras": {"required": False, "allow_blank": True},
        }


class ProdutoUpdateSerializer(ProdutoCreateSerializer):
    class Meta(ProdutoCreateSerializer.Meta):
        fields = ProdutoCreateSerializer.Meta.fields


class MovimentacaoSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)

    def get_fornecedor_nome(self, obj) -> str | None:
        if not obj.fornecedor:
            return None
        return str(obj.fornecedor)

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            "id",
            "company_id",
            "produto",
            "produto_nome",
            "produto_sku",
            "tipo",
            "quantidade_delta",
            "estoque_antes",
            "estoque_depois",
            "custo_unitario",
            "valor_total",
            "fornecedor",
            "fornecedor_nome",
            "motivo",
            "observacao",
            "status",
            "created_by",
            "created_by_nome",
            "movimentacao_cancelada",
            "idempotency_key",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class _MovimentacaoBaseSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {
        "produto": Produto,
        "fornecedor": Fornecedor,
    }

    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.none())
    fornecedor = serializers.PrimaryKeyRelatedField(
        queryset=Fornecedor.objects.none(),
        required=False,
        allow_null=True,
    )
    custo_unitario = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )
    motivo = serializers.CharField(max_length=255, required=False, allow_blank=True)
    observacao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class EntradaEstoqueSerializer(_MovimentacaoBaseSerializer):
    quantidade = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )


class SaidaEstoqueSerializer(_MovimentacaoBaseSerializer):
    quantidade = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )

    def validate(self, attrs):
        attrs.pop("fornecedor", None)
        attrs.pop("custo_unitario", None)
        return attrs


class AjusteEstoqueSerializer(_MovimentacaoBaseSerializer):
    quantidade = serializers.DecimalField(max_digits=14, decimal_places=3)
    motivo = serializers.CharField(max_length=255)

    def validate_quantidade(self, value):
        if value == Decimal("0.000"):
            raise ValidationError("Quantidade do ajuste não pode ser zero.")
        return value

    def validate(self, attrs):
        attrs.pop("fornecedor", None)
        attrs["quantidade_delta"] = attrs.pop("quantidade")
        return attrs


class DevolucaoEstoqueSerializer(_MovimentacaoBaseSerializer):
    quantidade = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    motivo = serializers.CharField(max_length=255)

    def validate(self, attrs):
        attrs.pop("fornecedor", None)
        attrs.pop("custo_unitario", None)
        return attrs


class CancelamentoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=255)
    observacao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
