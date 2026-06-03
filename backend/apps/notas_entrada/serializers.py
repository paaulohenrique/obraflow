from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import BaseModelSerializer
from apps.estoque.models import FormaVendaProduto, Fornecedor, Produto
from apps.financeiro.models import CategoriaFinanceira

from .models import HistoricoNotaFiscalEntrada, ItemNotaFiscalEntrada, NotaFiscalEntrada


class RejectCompanyPayloadMixin:
    def run_validation(self, data=serializers.empty):
        if isinstance(data, dict) and {"company", "company_id"} & set(data):
            raise ValidationError({
                "company": "Empresa é definida pelo usuário autenticado e não deve ser enviada."
            })
        return super().run_validation(data)


class TenantScopedSerializerMixin(RejectCompanyPayloadMixin):
    """Filtra querysets de PKRelatedFields para o tenant do usuário autenticado."""
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


# ── Upload ────────────────────────────────────────────────────────────────────


class UploadXMLSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    arquivo = serializers.FileField()
    observacao = serializers.CharField(required=False, allow_blank=True, max_length=500)
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)


# ── Importar por Chave (V2 stub) ──────────────────────────────────────────────


class ImportarChaveSerializer(serializers.Serializer):
    chave_acesso = serializers.CharField(min_length=44, max_length=44)

    def validate_chave_acesso(self, value):
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) != 44:
            raise ValidationError("Chave de acesso deve conter exatamente 44 dígitos numéricos.")
        return digits


# ── Itens ─────────────────────────────────────────────────────────────────────


class ItemNotaListSerializer(BaseModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, default=None)
    produto_id = serializers.UUIDField(source="produto.id", read_only=True, default=None)
    forma_venda_nome = serializers.SerializerMethodField()
    forma_venda_fator = serializers.SerializerMethodField()
    quantidade_convertida = serializers.SerializerMethodField()

    def get_forma_venda_nome(self, obj) -> str | None:
        if not obj.forma_venda_id:
            return None
        fv = obj.forma_venda
        return fv.nome if fv else None

    def get_forma_venda_fator(self, obj) -> str | None:
        if not obj.forma_venda_id:
            return None
        fv = obj.forma_venda
        return str(fv.fator_conversao) if fv else None

    def get_quantidade_convertida(self, obj) -> str | None:
        """Quantidade que será lançada no estoque (unidade base do produto)."""
        if not obj.forma_venda_id:
            return None
        fv = obj.forma_venda
        if not fv:
            return None
        return str(fv.converter(obj.quantidade))

    class Meta:
        model = ItemNotaFiscalEntrada
        fields = [
            "id",
            "ordem",
            "descricao_original",
            "codigo_fornecedor",
            "codigo_barras",
            "ncm",
            "cfop",
            "unidade",
            "quantidade",
            "valor_unitario",
            "valor_total_item",
            "custo_unitario",
            "valor_ipi_item",
            "valor_icms_item",
            "produto",
            "produto_id",
            "produto_nome",
            "forma_venda",
            "forma_venda_nome",
            "forma_venda_fator",
            "quantidade_convertida",
            "movimentacao_estoque",
            "ignorado",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ItemNotaUpdateSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"produto": Produto, "forma_venda": FormaVendaProduto}

    produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.none(),
        required=False,
        allow_null=True,
    )
    forma_venda = serializers.PrimaryKeyRelatedField(
        queryset=FormaVendaProduto.objects.none(),
        required=False,
        allow_null=True,
    )
    custo_unitario = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )
    ignorado = serializers.BooleanField(required=False)

    def validate(self, attrs):
        produto = attrs.get("produto")
        forma_venda = attrs.get("forma_venda")

        if forma_venda is not None and produto is not None:
            if forma_venda.produto_id != produto.pk:
                raise ValidationError({
                    "forma_venda": "Forma de venda não pertence ao produto selecionado."
                })
        if forma_venda is not None and not forma_venda.ativo:
            raise ValidationError({"forma_venda": "Forma de venda está inativa."})
        return attrs


class SugestoesProdutoSerializer(BaseModelSerializer):
    similarity = serializers.FloatField(read_only=True, default=None)

    class Meta:
        model = Produto
        fields = ["id", "nome", "sku", "codigo_barras", "estoque_atual", "preco_compra", "similarity"]
        read_only_fields = fields


# ── Nota ─────────────────────────────────────────────────────────────────────


class NotaFiscalEntradaListSerializer(BaseModelSerializer):
    criado_por_nome = serializers.CharField(source="criado_por.name", read_only=True, default=None)
    fornecedor_nome_final = serializers.SerializerMethodField()
    itens_total = serializers.SerializerMethodField()
    itens_sem_produto = serializers.SerializerMethodField()

    class Meta:
        model = NotaFiscalEntrada
        fields = [
            "id",
            "status",
            "numero",
            "serie",
            "modelo",
            "data_emissao",
            "data_entrada",
            "fornecedor",
            "fornecedor_nome_xml",
            "fornecedor_cnpj_xml",
            "fornecedor_nome_final",
            "valor_total",
            "valor_produtos",
            "valor_frete",
            "valor_desconto",
            "valor_icms",
            "valor_ipi",
            "chave_acesso",
            "conta_pagar",
            "criado_por",
            "criado_por_nome",
            "itens_total",
            "itens_sem_produto",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_fornecedor_nome_final(self, obj) -> str:
        return str(obj.fornecedor) if obj.fornecedor else obj.fornecedor_nome_xml

    def get_itens_total(self, obj) -> int:
        return obj.itens.filter(deleted_at__isnull=True).count()

    def get_itens_sem_produto(self, obj) -> int:
        return obj.itens.filter(deleted_at__isnull=True, produto__isnull=True, ignorado=False).count()


class NotaFiscalEntradaDetailSerializer(NotaFiscalEntradaListSerializer):
    confirmado_por_nome = serializers.CharField(source="confirmado_por.name", read_only=True, default=None)
    rejeitado_por_nome = serializers.CharField(source="rejeitado_por.name", read_only=True, default=None)
    itens = ItemNotaListSerializer(many=True, read_only=True)

    class Meta(NotaFiscalEntradaListSerializer.Meta):
        fields = NotaFiscalEntradaListSerializer.Meta.fields + [
            "sha256",
            "xml_file",
            "payload_extraido",
            "confirmado_por",
            "confirmado_por_nome",
            "confirmado_em",
            "rejeitado_por",
            "rejeitado_por_nome",
            "rejeitado_em",
            "motivo_rejeicao",
            "erro_codigo",
            "erro_mensagem",
            "observacao",
            "idempotency_key",
            "boleto",
            "itens",
        ]
        read_only_fields = fields


# ── Ações ─────────────────────────────────────────────────────────────────────


class VincularFornecedorSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"fornecedor": Fornecedor}

    fornecedor = serializers.PrimaryKeyRelatedField(queryset=Fornecedor.objects.none())


class DadosContaPagarSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"categoria": CategoriaFinanceira}
    categoria = serializers.PrimaryKeyRelatedField(queryset=CategoriaFinanceira.objects.none())
    data_vencimento = serializers.DateField()
    observacao = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_categoria(self, value):
        if value.tipo != CategoriaFinanceira.TIPO_DESPESA:
            raise ValidationError("Conta a pagar exige categoria de despesa.")
        if not value.ativa or not value.is_active:
            raise ValidationError("Categoria financeira inativa.")
        return value


class ConfirmarNotaSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    criar_conta_pagar = serializers.BooleanField(default=False)
    dados_conta_pagar = DadosContaPagarSerializer(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("criar_conta_pagar") and not attrs.get("dados_conta_pagar"):
            raise ValidationError({
                "dados_conta_pagar": "Obrigatório quando criar_conta_pagar=true."
            })
        return attrs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        company_id = getattr(getattr(request, "user", None), "company_id", None)
        if company_id and "dados_conta_pagar" in self.fields:
            nested = self.fields["dados_conta_pagar"]
            if hasattr(nested, "fields") and "categoria" in nested.fields:
                nested.fields["categoria"].queryset = CategoriaFinanceira.objects.filter(
                    company_id=company_id,
                    deleted_at__isnull=True,
                    tipo=CategoriaFinanceira.TIPO_DESPESA,
                )


class RejeitarNotaSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)


# ── Histórico ─────────────────────────────────────────────────────────────────


class HistoricoNotaSerializer(BaseModelSerializer):
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True, default=None)

    class Meta:
        model = HistoricoNotaFiscalEntrada
        fields = [
            "id",
            "evento",
            "descricao",
            "before",
            "after",
            "metadata",
            "request_id",
            "created_by",
            "created_by_nome",
            "created_at",
        ]
        read_only_fields = fields


# ── Dashboard ─────────────────────────────────────────────────────────────────


class DashboardNotasSerializer(serializers.Serializer):
    notas_importadas_hoje = serializers.IntegerField()
    aguardando_revisao = serializers.IntegerField()
    confirmadas_mes = serializers.IntegerField()
    rejeitadas_mes = serializers.IntegerField()
    valor_total_importado_mes = serializers.DecimalField(max_digits=14, decimal_places=2)
    valor_total_confirmado_mes = serializers.DecimalField(max_digits=14, decimal_places=2)
    movimentacoes_estoque_geradas_mes = serializers.IntegerField()
    contas_pagar_criadas_mes = serializers.IntegerField()
    fornecedores_novos_detectados = serializers.IntegerField()
    itens_sem_produto_pendentes = serializers.IntegerField()
