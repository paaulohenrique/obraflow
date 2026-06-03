from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import BaseModelSerializer
from apps.estoque.models import Fornecedor

from .models import (
    CaixaDiario,
    CategoriaFinanceira,
    ConfiguracaoFinanceiraOperacional,
    ContaFinanceira,
    ContaPagar,
    LancamentoFinanceiro,
)
from .services.configuracao import destinos_pdv


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


class ContaFinanceiraListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ContaFinanceira
        fields = [
            "id",
            "company_id",
            "nome",
            "tipo",
            "saldo_atual",
            "ativo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ContaFinanceiraDetailSerializer(ContaFinanceiraListSerializer):
    class Meta(ContaFinanceiraListSerializer.Meta):
        fields = ContaFinanceiraListSerializer.Meta.fields + ["observacao"]
        read_only_fields = fields


class ContaFinanceiraCreateSerializer(RejectCompanyPayloadMixin, serializers.ModelSerializer):
    class Meta:
        model = ContaFinanceira
        fields = ["nome", "tipo", "ativo", "observacao"]
        extra_kwargs = {
            "ativo": {"required": False},
            "observacao": {"required": False, "allow_blank": True},
        }


class ContaFinanceiraUpdateSerializer(RejectCompanyPayloadMixin, serializers.ModelSerializer):
    class Meta:
        model = ContaFinanceira
        fields = ["nome", "tipo", "ativo", "observacao"]
        extra_kwargs = {
            "nome": {"required": False},
            "tipo": {"required": False},
            "ativo": {"required": False},
            "observacao": {"required": False, "allow_blank": True},
        }


class DestinoPdvSerializer(serializers.Serializer):
    forma_pagamento = serializers.CharField()
    conta = serializers.UUIDField(allow_null=True)
    conta_nome = serializers.CharField(allow_blank=True)
    conta_tipo = serializers.CharField(allow_blank=True)
    configurada = serializers.BooleanField()


class ConfiguracaoFinanceiraOperacionalSerializer(TenantScopedSerializerMixin, BaseModelSerializer):
    tenant_scoped_fields = {
        "conta_pix": ContaFinanceira,
        "conta_dinheiro": ContaFinanceira,
        "conta_cartao": ContaFinanceira,
        "conta_transferencia": ContaFinanceira,
    }
    company_id = serializers.UUIDField(read_only=True)
    conta_pix_nome = serializers.CharField(source="conta_pix.nome", read_only=True)
    conta_dinheiro_nome = serializers.CharField(source="conta_dinheiro.nome", read_only=True)
    conta_cartao_nome = serializers.CharField(source="conta_cartao.nome", read_only=True)
    conta_transferencia_nome = serializers.CharField(source="conta_transferencia.nome", read_only=True)
    updated_by_nome = serializers.CharField(source="updated_by.name", read_only=True)
    destinos_pdv = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracaoFinanceiraOperacional
        fields = [
            "id",
            "company_id",
            "conta_pix",
            "conta_pix_nome",
            "conta_dinheiro",
            "conta_dinheiro_nome",
            "conta_cartao",
            "conta_cartao_nome",
            "conta_transferencia",
            "conta_transferencia_nome",
            "destinos_pdv",
            "updated_by",
            "updated_by_nome",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "conta_pix_nome",
            "conta_dinheiro_nome",
            "conta_cartao_nome",
            "conta_transferencia_nome",
            "destinos_pdv",
            "updated_by",
            "updated_by_nome",
            "is_active",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "conta_pix": {"required": False, "allow_null": True},
            "conta_dinheiro": {"required": False, "allow_null": True},
            "conta_cartao": {"required": False, "allow_null": True},
            "conta_transferencia": {"required": False, "allow_null": True},
        }

    def get_destinos_pdv(self, obj):
        resolvidos = destinos_pdv(company_id=obj.company_id)
        configuradas = {
            "PIX": obj.conta_pix_id,
            "DINHEIRO": obj.conta_dinheiro_id,
            "CARTAO": obj.conta_cartao_id,
            "TRANSFERENCIA": obj.conta_transferencia_id,
        }
        data = []
        for forma_pagamento, conta in resolvidos.items():
            data.append({
                "forma_pagamento": forma_pagamento,
                "conta": conta.pk if conta else None,
                "conta_nome": conta.nome if conta else "",
                "conta_tipo": conta.tipo if conta else "",
                "configurada": bool(configuradas.get(forma_pagamento)),
            })
        return DestinoPdvSerializer(data, many=True).data


class AjusteSaldoSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"categoria": CategoriaFinanceira}

    tipo = serializers.ChoiceField(choices=LancamentoFinanceiro.TIPO_CHOICES)
    valor = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    categoria = serializers.PrimaryKeyRelatedField(
        queryset=CategoriaFinanceira.objects.none(),
        required=False,
        allow_null=True,
    )
    data_lancamento = serializers.DateTimeField(required=False)
    descricao = serializers.CharField(required=False, allow_blank=True)
    forma_pagamento = serializers.ChoiceField(
        choices=LancamentoFinanceiro.FORMA_CHOICES,
        required=False,
    )
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class CategoriaFinanceiraSerializer(RejectCompanyPayloadMixin, BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = CategoriaFinanceira
        fields = [
            "id",
            "company_id",
            "nome",
            "tipo",
            "descricao",
            "ativa",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "is_active", "created_at", "updated_at"]
        extra_kwargs = {
            "descricao": {"required": False, "allow_blank": True},
            "ativa": {"required": False},
        }


class LancamentoFinanceiroListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    conta_financeira_nome = serializers.CharField(source="conta_financeira.nome", read_only=True)
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "id",
            "company_id",
            "conta_financeira",
            "conta_financeira_nome",
            "categoria",
            "categoria_nome",
            "caixa_diario",
            "tipo",
            "valor",
            "data_lancamento",
            "descricao",
            "origem_tipo",
            "origem_id",
            "forma_pagamento",
            "status",
            "created_by",
            "created_by_nome",
            "estorno_de",
            "idempotency_key",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LancamentoFinanceiroDetailSerializer(LancamentoFinanceiroListSerializer):
    cancelled_by_nome = serializers.CharField(source="cancelled_by.name", read_only=True)

    class Meta(LancamentoFinanceiroListSerializer.Meta):
        fields = LancamentoFinanceiroListSerializer.Meta.fields + [
            "cancelled_by",
            "cancelled_by_nome",
            "cancelled_at",
            "motivo_cancelamento",
            "metadata",
        ]
        read_only_fields = fields


class LancamentoFinanceiroCreateSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {
        "conta_financeira": ContaFinanceira,
        "categoria": CategoriaFinanceira,
        "caixa_diario": CaixaDiario,
    }

    conta_financeira = serializers.PrimaryKeyRelatedField(queryset=ContaFinanceira.objects.none())
    categoria = serializers.PrimaryKeyRelatedField(queryset=CategoriaFinanceira.objects.none())
    caixa_diario = serializers.PrimaryKeyRelatedField(
        queryset=CaixaDiario.objects.none(),
        required=False,
        allow_null=True,
    )
    tipo = serializers.ChoiceField(choices=LancamentoFinanceiro.TIPO_CHOICES)
    valor = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    data_lancamento = serializers.DateTimeField(required=False)
    descricao = serializers.CharField(required=False, allow_blank=True)
    forma_pagamento = serializers.ChoiceField(
        choices=LancamentoFinanceiro.FORMA_CHOICES,
        required=False,
    )
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        categoria = attrs["categoria"]
        tipo = attrs["tipo"]
        if tipo == LancamentoFinanceiro.TIPO_ENTRADA and categoria.tipo != CategoriaFinanceira.TIPO_RECEITA:
            raise ValidationError({"categoria": "Entrada exige categoria de receita."})
        if tipo == LancamentoFinanceiro.TIPO_SAIDA and categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
            raise ValidationError({"categoria": "Saída exige categoria de despesa."})
        if not attrs["conta_financeira"].ativo:
            raise ValidationError({"conta_financeira": "Conta financeira inativa."})
        return attrs


class CancelarLancamentoSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)


class ContaPagarListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)
    is_parcial = serializers.BooleanField(read_only=True)
    is_atrasada = serializers.BooleanField(read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)

    class Meta:
        model = ContaPagar
        fields = [
            "id",
            "company_id",
            "fornecedor",
            "fornecedor_nome",
            "descricao",
            "categoria",
            "categoria_nome",
            "valor_total",
            "valor_pago",
            "valor_restante",
            "data_emissao",
            "data_vencimento",
            "data_pagamento",
            "status",
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

    def get_fornecedor_nome(self, obj) -> str:
        return str(obj.fornecedor) if obj.fornecedor else ""


class ContaPagarDetailSerializer(ContaPagarListSerializer):
    cancelled_by_nome = serializers.CharField(source="cancelled_by.name", read_only=True)

    class Meta(ContaPagarListSerializer.Meta):
        fields = ContaPagarListSerializer.Meta.fields + [
            "observacao",
            "cancelled_by",
            "cancelled_by_nome",
            "cancelled_at",
            "motivo_cancelamento",
        ]
        read_only_fields = fields


class ContaPagarCreateSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"fornecedor": Fornecedor, "categoria": CategoriaFinanceira}

    fornecedor = serializers.PrimaryKeyRelatedField(
        queryset=Fornecedor.objects.none(),
        required=False,
        allow_null=True,
    )
    descricao = serializers.CharField(max_length=255)
    categoria = serializers.PrimaryKeyRelatedField(queryset=CategoriaFinanceira.objects.none())
    valor_total = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    data_emissao = serializers.DateField(required=False)
    data_vencimento = serializers.DateField()
    observacao = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["categoria"].tipo != CategoriaFinanceira.TIPO_DESPESA:
            raise ValidationError({"categoria": "Conta a pagar exige categoria de despesa."})
        if "data_emissao" in attrs and attrs["data_emissao"] > attrs["data_vencimento"]:
            raise ValidationError({"data_emissao": "Emissão não pode ser após o vencimento."})
        return attrs


class ContaPagarUpdateSerializer(ContaPagarCreateSerializer):
    descricao = serializers.CharField(max_length=255, required=False)
    categoria = serializers.PrimaryKeyRelatedField(
        queryset=CategoriaFinanceira.objects.none(),
        required=False,
    )
    valor_total = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    data_vencimento = serializers.DateField(required=False)

    def validate(self, attrs):
        categoria = attrs.get("categoria")
        if categoria and categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
            raise ValidationError({"categoria": "Conta a pagar exige categoria de despesa."})
        data_emissao = attrs.get("data_emissao", getattr(self.instance, "data_emissao", None))
        data_vencimento = attrs.get("data_vencimento", getattr(self.instance, "data_vencimento", None))
        if data_emissao and data_vencimento and data_emissao > data_vencimento:
            raise ValidationError({"data_emissao": "Emissão não pode ser após o vencimento."})
        return attrs


class PagarContaPagarSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"conta_financeira": ContaFinanceira}

    conta_financeira = serializers.PrimaryKeyRelatedField(queryset=ContaFinanceira.objects.none())
    valor = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    forma_pagamento = serializers.ChoiceField(choices=LancamentoFinanceiro.FORMA_CHOICES)
    data_pagamento = serializers.DateTimeField(required=False)
    descricao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class CancelarContaPagarSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)


class CaixaDiarioListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    conta_financeira_nome = serializers.CharField(source="conta_financeira.nome", read_only=True)
    aberto_por_nome = serializers.CharField(source="aberto_por.name", read_only=True)
    fechado_por_nome = serializers.CharField(source="fechado_por.name", read_only=True)

    class Meta:
        model = CaixaDiario
        fields = [
            "id",
            "company_id",
            "conta_financeira",
            "conta_financeira_nome",
            "data",
            "status",
            "saldo_inicial",
            "total_entradas",
            "total_saidas",
            "saldo_final",
            "aberto_por",
            "aberto_por_nome",
            "fechado_por",
            "fechado_por_nome",
            "aberto_em",
            "fechado_em",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CaixaDiarioDetailSerializer(CaixaDiarioListSerializer):
    class Meta(CaixaDiarioListSerializer.Meta):
        fields = CaixaDiarioListSerializer.Meta.fields + ["observacao"]
        read_only_fields = fields


class AbrirCaixaSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"conta_financeira": ContaFinanceira}

    conta_financeira = serializers.PrimaryKeyRelatedField(queryset=ContaFinanceira.objects.none())
    data = serializers.DateField(required=False)
    observacao = serializers.CharField(required=False, allow_blank=True)


class FecharCaixaSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    observacao = serializers.CharField(required=False, allow_blank=True)


class ReabrirCaixaSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    observacao = serializers.CharField(required=False, allow_blank=True)


class DashboardFinanceiroSerializer(serializers.Serializer):
    recebido_hoje = serializers.DecimalField(max_digits=14, decimal_places=2)
    recebido_mes = serializers.DecimalField(max_digits=14, decimal_places=2)
    recebido_ano = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_contas_pagar_abertas = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_contas_pagar_vencidas = serializers.DecimalField(max_digits=14, decimal_places=2)
    saldo_caixa = serializers.DecimalField(max_digits=14, decimal_places=2)
    saldo_total_financeiro = serializers.DecimalField(max_digits=14, decimal_places=2)
    inadimplencia_valor_cobrado = serializers.DecimalField(max_digits=14, decimal_places=2)
    inadimplencia_valor_recuperado = serializers.DecimalField(max_digits=14, decimal_places=2)
    inadimplencia_percentual_recuperacao = serializers.FloatField()
    fluxo_diario = serializers.ListField(child=serializers.DictField())
    entradas_por_categoria = serializers.ListField(child=serializers.DictField())
    saidas_por_categoria = serializers.ListField(child=serializers.DictField())
