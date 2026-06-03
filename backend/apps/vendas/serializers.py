from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.clientes.models import Cliente
from apps.core.serializers import BaseModelSerializer
from apps.estoque.models import FormaVendaProduto, Produto
from apps.financeiro.models import ContaFinanceira

from .models import ItemVenda, Venda


class RejectCompanyPayloadMixin:
    def run_validation(self, data=serializers.empty):
        if isinstance(data, dict) and {"company", "company_id"} & set(data):
            raise ValidationError({
                "company": "Empresa é definida pelo usuário autenticado e não deve ser enviada."
            })
        return super().run_validation(data)


class TenantScopedMixin(RejectCompanyPayloadMixin):
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


# ─── Item de Venda ────────────────────────────────────────────────────────────

class ItemVendaListSerializer(BaseModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    produto_unidade_sigla = serializers.CharField(source="produto.unidade_sigla", read_only=True)
    forma_venda_nome = serializers.CharField(source="forma_venda.nome", read_only=True)

    class Meta:
        model = ItemVenda
        fields = [
            "id",
            "produto",
            "produto_nome",
            "produto_sku",
            "produto_unidade_sigla",
            "forma_venda",
            "forma_venda_nome",
            "quantidade_informada",
            "quantidade",
            "preco_unitario",
            "subtotal",
            "custo_unitario_historico",
            "custo_total_historico",
            "created_at",
        ]
        read_only_fields = fields


class ItemVendaCreateSerializer(serializers.Serializer):
    # Sem TenantScopedMixin: contexto não está disponível em serializer aninhado.
    # A validação de empresa é feita no service.
    produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.filter(deleted_at__isnull=True, is_active=True)
    )
    forma_venda = serializers.PrimaryKeyRelatedField(
        queryset=FormaVendaProduto.objects.filter(deleted_at__isnull=True, ativo=True),
        required=False,
        allow_null=True,
    )
    quantidade_informada = serializers.DecimalField(
        max_digits=15, decimal_places=3, min_value=Decimal("0.001")
    )
    preco_unitario = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00")
    )

    def validate(self, attrs):
        forma_venda = attrs.get("forma_venda")
        produto = attrs["produto"]
        if forma_venda and forma_venda.produto_id != produto.pk:
            raise ValidationError({"forma_venda": "Forma de venda não pertence ao produto informado."})
        return attrs


# ─── Venda ────────────────────────────────────────────────────────────────────

class VendaListSerializer(BaseModelSerializer):
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    conta_financeira_nome = serializers.CharField(source="conta_financeira.nome", read_only=True)
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)
    total_itens = serializers.SerializerMethodField()

    class Meta:
        model = Venda
        fields = [
            "id",
            "numero",
            "cliente",
            "cliente_nome",
            "status",
            "valor_subtotal",
            "desconto",
            "valor_total",
            "forma_pagamento",
            "conta_financeira",
            "conta_financeira_nome",
            "total_itens",
            "created_by",
            "created_by_nome",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_total_itens(self, obj) -> int:
        return obj.itens.filter(deleted_at__isnull=True).count()


class VendaDetailSerializer(VendaListSerializer):
    itens = ItemVendaListSerializer(many=True, read_only=True)
    cancelled_by_nome = serializers.CharField(source="cancelled_by.name", read_only=True)

    class Meta(VendaListSerializer.Meta):
        fields = VendaListSerializer.Meta.fields + [
            "itens",
            "observacao",
            "cancelled_by",
            "cancelled_by_nome",
            "cancelled_at",
            "motivo_cancelamento",
        ]
        read_only_fields = fields


class VendaCreateSerializer(TenantScopedMixin, serializers.Serializer):
    tenant_scoped_fields = {
        "cliente": Cliente,
        "conta_financeira": ContaFinanceira,
    }

    itens = ItemVendaCreateSerializer(many=True)
    forma_pagamento = serializers.ChoiceField(choices=Venda.FORMA_CHOICES)
    conta_financeira = serializers.PrimaryKeyRelatedField(queryset=ContaFinanceira.objects.none())
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.none(),
        required=False,
        allow_null=True,
    )
    desconto = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00"),
        required=False, default=Decimal("0.00"),
    )
    observacao = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_itens(self, value):
        if not value:
            raise ValidationError("A venda deve ter pelo menos 1 item.")
        return value

    def validate(self, attrs):
        conta = attrs["conta_financeira"]
        if not conta.ativo:
            raise ValidationError({"conta_financeira": "Conta financeira inativa."})
        return attrs


class CancelarVendaSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)


class DashboardVendasSerializer(serializers.Serializer):
    total_hoje = serializers.DecimalField(max_digits=14, decimal_places=2)
    count_hoje = serializers.IntegerField()
    total_mes = serializers.DecimalField(max_digits=14, decimal_places=2)
    count_mes = serializers.IntegerField()
    ticket_medio = serializers.DecimalField(max_digits=14, decimal_places=2)
