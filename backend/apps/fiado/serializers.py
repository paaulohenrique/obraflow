from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.clientes.models import Cliente
from apps.core.serializers import BaseModelSerializer
from apps.estoque.models import FormaVendaProduto, Produto
from apps.financeiro.models import ContaFinanceira

from .models import ContaFiado, HistoricoFiado, ItemFiado, PagamentoFiado


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


class ContaFiadoListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    cliente_cpf_cnpj = serializers.CharField(source="cliente.cpf_cnpj", read_only=True)
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)
    is_parcial = serializers.BooleanField(read_only=True)
    is_atrasada = serializers.BooleanField(read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)

    class Meta:
        model = ContaFiado
        fields = [
            "id",
            "company_id",
            "cliente",
            "cliente_nome",
            "cliente_cpf_cnpj",
            "status",
            "valor_total",
            "valor_pago",
            "valor_restante",
            "data_abertura",
            "data_vencimento",
            "data_fechamento",
            "is_parcial",
            "is_atrasada",
            "dias_atraso",
            "created_by",
            "created_by_nome",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ContaFiadoDetailSerializer(ContaFiadoListSerializer):
    closed_by_nome = serializers.CharField(source="closed_by.name", read_only=True)
    cancelled_by_nome = serializers.CharField(source="cancelled_by.name", read_only=True)

    class Meta(ContaFiadoListSerializer.Meta):
        fields = ContaFiadoListSerializer.Meta.fields + [
            "observacao",
            "closed_by",
            "closed_by_nome",
            "cancelled_by",
            "cancelled_by_nome",
            "cancelled_at",
            "motivo_cancelamento",
        ]
        read_only_fields = fields


class ContaFiadoCreateSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    tenant_scoped_fields = {"cliente": Cliente}

    class Meta:
        model = ContaFiado
        fields = ["cliente", "data_vencimento", "observacao"]
        extra_kwargs = {
            "data_vencimento": {"required": False, "allow_null": True},
            "observacao": {"required": False, "allow_blank": True},
        }


class ContaFiadoUpdateSerializer(RejectCompanyPayloadMixin, serializers.ModelSerializer):
    class Meta:
        model = ContaFiado
        fields = ["data_vencimento", "observacao"]
        extra_kwargs = {
            "data_vencimento": {"required": False, "allow_null": True},
            "observacao": {"required": False, "allow_blank": True},
        }


class ContaFiadoCancelSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)
    observacao = serializers.CharField(required=False, allow_blank=True)


class ItemFiadoSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    forma_venda_nome = serializers.SerializerMethodField()
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)
    cancelled_by_nome = serializers.CharField(source="cancelled_by.name", read_only=True)

    def get_forma_venda_nome(self, obj) -> str | None:
        if not obj.forma_venda_id:
            return None
        fv = obj.forma_venda
        return fv.nome if fv else None

    class Meta:
        model = ItemFiado
        fields = [
            "id",
            "company_id",
            "conta",
            "produto",
            "produto_nome",
            "produto_sku",
            "forma_venda",
            "forma_venda_nome",
            "quantidade_informada",
            "quantidade",
            "preco_unitario",
            "subtotal",
            "data_lancamento",
            "movimentacao_estoque",
            "movimentacao_cancelamento",
            "status",
            "created_by",
            "created_by_nome",
            "cancelled_by",
            "cancelled_by_nome",
            "cancelled_at",
            "motivo_cancelamento",
            "observacao",
            "idempotency_key",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ItemFiadoCreateSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"produto": Produto, "forma_venda": FormaVendaProduto}

    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.none())
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
    quantidade = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
    )
    preco_unitario = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )
    observacao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate(self, attrs):
        produto = attrs.get("produto")
        forma_venda = attrs.get("forma_venda")
        quantidade_informada = attrs.get("quantidade_informada")
        quantidade = attrs.get("quantidade")

        if forma_venda and produto and forma_venda.produto_id != produto.pk:
            raise ValidationError({"forma_venda": "Forma de venda não pertence a este produto."})
        if forma_venda and not forma_venda.ativo:
            raise ValidationError({"forma_venda": "Forma de venda está inativa."})

        if not quantidade and not (forma_venda and quantidade_informada):
            raise ValidationError(
                {"quantidade": "Informe quantidade ou forma_venda + quantidade_informada."}
            )
        return attrs


class ItemFiadoCancelSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)
    observacao = serializers.CharField(required=False, allow_blank=True)


class PagamentoFiadoSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)
    cancelled_by_nome = serializers.CharField(source="cancelled_by.name", read_only=True)

    class Meta:
        model = PagamentoFiado
        fields = [
            "id",
            "company_id",
            "conta",
            "valor",
            "forma_pagamento",
            "data_pagamento",
            "status",
            "observacao",
            "created_by",
            "created_by_nome",
            "cancelled_by",
            "cancelled_by_nome",
            "cancelled_at",
            "motivo_cancelamento",
            "idempotency_key",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PagamentoFiadoCreateSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"conta_financeira": ContaFinanceira}

    valor = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    forma_pagamento = serializers.ChoiceField(choices=PagamentoFiado.FORMA_CHOICES)
    conta_financeira = serializers.PrimaryKeyRelatedField(
        queryset=ContaFinanceira.objects.none(),
        required=False,
        allow_null=True,
    )
    data_pagamento = serializers.DateTimeField(required=False)
    observacao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class PagamentoFiadoCancelSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)
    observacao = serializers.CharField(required=False, allow_blank=True)


class HistoricoFiadoSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = HistoricoFiado
        fields = [
            "id",
            "company_id",
            "conta",
            "item",
            "pagamento",
            "evento",
            "descricao",
            "before",
            "after",
            "metadata",
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DashboardFiadoSerializer(serializers.Serializer):
    total_em_aberto = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_atrasado = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_recebido_hoje = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_recebido_mes = serializers.DecimalField(max_digits=14, decimal_places=2)
    contas_abertas = serializers.IntegerField()
    contas_atrasadas = serializers.IntegerField()
    clientes_devedores = serializers.IntegerField()
    ticket_medio_fiado = serializers.DecimalField(max_digits=14, decimal_places=2)
