from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import BaseModelSerializer
from apps.empresas.validators import clean_cnpj, is_valid_cnpj
from apps.fiscal.validators import validate_cest, validate_cfop, validate_ncm

from .models import (
    CategoriaProduto,
    FormaVendaProduto,
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


class FormaVendaProdutoSerializer(RejectCompanyPayloadMixin, BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    produto_id = serializers.UUIDField(read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    quantidade_convertida_exemplo = serializers.SerializerMethodField()

    def get_quantidade_convertida_exemplo(self, obj) -> str:
        sigla = obj.produto.unidade.sigla if obj.produto_id else "?"
        return f"1 {obj.unidade} baixa {obj.fator_conversao} {sigla} do estoque"

    class Meta:
        model = FormaVendaProduto
        fields = [
            "id",
            "company_id",
            "produto_id",
            "produto_nome",
            "nome",
            "codigo",
            "unidade",
            "fator_conversao",
            "preco_venda",
            "ativo",
            "padrao",
            "permite_fracionado",
            "quantidade_convertida_exemplo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "company_id", "produto_id", "produto_nome",
            "quantidade_convertida_exemplo", "is_active", "created_at", "updated_at",
        ]


class FormaVendaProdutoCreateSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    tenant_scoped_fields = {"produto": Produto}
    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.none())

    class Meta:
        model = FormaVendaProduto
        fields = [
            "produto",
            "nome",
            "codigo",
            "unidade",
            "fator_conversao",
            "preco_venda",
            "ativo",
            "padrao",
            "permite_fracionado",
        ]
        extra_kwargs = {
            "codigo": {"required": False, "allow_blank": True},
            "preco_venda": {"required": False},
            "ativo": {"required": False},
            "padrao": {"required": False},
            "permite_fracionado": {"required": False},
        }

    def validate_fator_conversao(self, value):
        if value <= Decimal("0"):
            raise ValidationError("Fator de conversão deve ser maior que zero.")
        return value


class FormaVendaProdutoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormaVendaProduto
        fields = [
            "nome",
            "codigo",
            "unidade",
            "fator_conversao",
            "preco_venda",
            "permite_fracionado",
        ]
        extra_kwargs = {
            "nome": {"required": False},
            "codigo": {"required": False, "allow_blank": True},
            "unidade": {"required": False},
            "fator_conversao": {"required": False},
            "preco_venda": {"required": False},
            "permite_fracionado": {"required": False},
        }

    def validate_fator_conversao(self, value):
        if value <= Decimal("0"):
            raise ValidationError("Fator de conversão deve ser maior que zero.")
        return value


class ProdutoListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    unidade_sigla = serializers.CharField(source="unidade.sigla", read_only=True)
    estoque_baixo = serializers.BooleanField(read_only=True)
    margem_percentual = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    cadastro_fiscal_pronto = serializers.BooleanField(read_only=True)

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
            "ncm",
            "cfop_padrao",
            "cst_csosn",
            "cest",
            "origem_mercadoria",
            "unidade_tributavel",
            "ean_tributavel",
            "codigo_beneficio_fiscal",
            "aliquota_icms",
            "aliquota_ipi",
            "aliquota_pis",
            "aliquota_cofins",
            "cadastro_fiscal_pronto",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProdutoDetailSerializer(ProdutoListSerializer):
    class Meta(ProdutoListSerializer.Meta):
        fields = ProdutoListSerializer.Meta.fields + ["descricao"]
        read_only_fields = fields


class ProdutoAuditoriaItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nome = serializers.CharField()
    sku = serializers.CharField(allow_blank=True)
    categoria_nome = serializers.CharField(allow_blank=True)
    unidade_sigla = serializers.CharField(allow_blank=True)
    preco_venda = serializers.DecimalField(max_digits=12, decimal_places=2)
    estoque_atual = serializers.DecimalField(max_digits=14, decimal_places=3)
    is_active = serializers.BooleanField()


class ProdutoAuditoriaGrupoSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = ProdutoAuditoriaItemSerializer(many=True)


class ProdutoAuditoriaOperacionalSerializer(serializers.Serializer):
    sem_forma_venda = ProdutoAuditoriaGrupoSerializer()
    sem_categoria = ProdutoAuditoriaGrupoSerializer()
    sem_unidade = ProdutoAuditoriaGrupoSerializer()
    sem_preco = ProdutoAuditoriaGrupoSerializer()
    inativos = ProdutoAuditoriaGrupoSerializer()


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
            "ncm",
            "cfop_padrao",
            "cst_csosn",
            "cest",
            "origem_mercadoria",
            "unidade_tributavel",
            "ean_tributavel",
            "codigo_beneficio_fiscal",
            "aliquota_icms",
            "aliquota_ipi",
            "aliquota_pis",
            "aliquota_cofins",
        ]
        extra_kwargs = {
            "fornecedor_principal": {"required": False, "allow_null": True},
            "descricao": {"required": False, "allow_blank": True},
            "sku": {"required": False, "allow_blank": True},
            "codigo_barras": {"required": False, "allow_blank": True},
            "ncm": {"required": False, "allow_blank": True},
            "cfop_padrao": {"required": False, "allow_blank": True},
            "cst_csosn": {"required": False, "allow_blank": True},
            "cest": {"required": False, "allow_blank": True},
            "origem_mercadoria": {"required": False},
            "unidade_tributavel": {"required": False, "allow_blank": True},
            "ean_tributavel": {"required": False, "allow_blank": True},
            "codigo_beneficio_fiscal": {"required": False, "allow_blank": True},
            "aliquota_icms": {"required": False},
            "aliquota_ipi": {"required": False},
            "aliquota_pis": {"required": False},
            "aliquota_cofins": {"required": False},
        }

    def validate_ncm(self, value):
        return validate_ncm(value)

    def validate_cfop_padrao(self, value):
        return validate_cfop(value)

    def validate_cest(self, value):
        return validate_cest(value)


class ProdutoUpdateSerializer(ProdutoCreateSerializer):
    class Meta(ProdutoCreateSerializer.Meta):
        fields = ProdutoCreateSerializer.Meta.fields


class MovimentacaoSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)
    forma_venda_nome = serializers.SerializerMethodField()
    quantidade_convertida = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True
    )

    def get_fornecedor_nome(self, obj) -> str | None:
        if not obj.fornecedor:
            return None
        return str(obj.fornecedor)

    def get_forma_venda_nome(self, obj) -> str | None:
        if not obj.forma_venda_id:
            return None
        fv = obj.forma_venda
        return fv.nome if fv else None

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
            "quantidade_convertida",
            "forma_venda",
            "forma_venda_nome",
            "quantidade_informada",
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
        "forma_venda": FormaVendaProduto,
    }

    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.none())
    fornecedor = serializers.PrimaryKeyRelatedField(
        queryset=Fornecedor.objects.none(),
        required=False,
        allow_null=True,
    )
    forma_venda = serializers.PrimaryKeyRelatedField(
        queryset=FormaVendaProduto.objects.none(),
        required=False,
        allow_null=True,
    )
    quantidade_informada = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
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

    def validate(self, attrs):
        produto = attrs.get("produto")
        forma_venda = attrs.get("forma_venda")
        quantidade_informada = attrs.get("quantidade_informada")

        if forma_venda and produto and forma_venda.produto_id != produto.pk:
            raise ValidationError({"forma_venda": "Forma de venda não pertence a este produto."})
        if forma_venda and not forma_venda.ativo:
            raise ValidationError({"forma_venda": "Forma de venda está inativa."})

        # Converte quantidade via forma de venda se ambos fornecidos
        if forma_venda and quantidade_informada:
            from apps.estoque.services.forma_venda import converter_quantidade
            attrs["quantidade"] = converter_quantidade(
                forma_venda=forma_venda,
                quantidade=quantidade_informada,
            )
        return attrs


class EntradaEstoqueSerializer(_MovimentacaoBaseSerializer):
    quantidade = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("quantidade") and not (attrs.get("forma_venda") and attrs.get("quantidade_informada")):
            raise ValidationError({"quantidade": "Informe quantidade ou forma_venda + quantidade_informada."})
        return attrs


class SaidaEstoqueSerializer(_MovimentacaoBaseSerializer):
    quantidade = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs.pop("fornecedor", None)
        attrs.pop("custo_unitario", None)
        if not attrs.get("quantidade") and not (attrs.get("forma_venda") and attrs.get("quantidade_informada")):
            raise ValidationError({"quantidade": "Informe quantidade ou forma_venda + quantidade_informada."})
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
        required=False,
    )
    motivo = serializers.CharField(max_length=255)

    def validate(self, attrs):
        attrs = super().validate(attrs)  # aplica conversão via forma_venda se fornecida
        attrs.pop("fornecedor", None)
        attrs.pop("custo_unitario", None)
        if not attrs.get("quantidade") and not (attrs.get("forma_venda") and attrs.get("quantidade_informada")):
            raise ValidationError({"quantidade": "Informe quantidade ou forma_venda + quantidade_informada."})
        return attrs


class CancelamentoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=255)
    observacao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
