from rest_framework import serializers

from apps.core.serializers import BaseModelSerializer
from apps.fiado.models import ContaFiado
from apps.notificacoes.models import Notificacao

from .models import ConfiguracaoCobranca


TIPOS_COBRANCA_CHOICES = [
    Notificacao.TIPO_COBRANCA_FIADO,
    Notificacao.TIPO_LEMBRETE_VENCIMENTO,
    Notificacao.TIPO_COBRANCA_1_DIA,
    Notificacao.TIPO_COBRANCA_7_DIAS,
    Notificacao.TIPO_COBRANCA_15_DIAS,
    Notificacao.TIPO_COBRANCA_30_DIAS,
]


class ConfiguracaoCobrancaSerializer(BaseModelSerializer):
    class Meta:
        model = ConfiguracaoCobranca
        fields = [
            "id",
            "ativo",
            "enviar_1_dia_antes",
            "enviar_no_vencimento",
            "enviar_7_dias_apos",
            "enviar_15_dias_apos",
            "enviar_30_dias_apos",
            "updated_by",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["id", "updated_by", "created_at", "updated_at", "is_active"]


class CobrancaContaSerializer(BaseModelSerializer):
    cliente_id = serializers.UUIDField(source="cliente.id", read_only=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    cliente_documento = serializers.CharField(source="cliente.cpf_cnpj", read_only=True)
    cliente_telefone = serializers.CharField(source="cliente.telefone", read_only=True)
    cliente_whatsapp = serializers.CharField(source="cliente.whatsapp", read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)
    status_cobranca = serializers.CharField(read_only=True)
    ultima_cobranca_id = serializers.UUIDField(read_only=True, allow_null=True)
    ultima_cobranca_tipo = serializers.CharField(read_only=True, allow_null=True)
    ultima_cobranca_em = serializers.DateTimeField(read_only=True, allow_null=True)
    tem_contato = serializers.SerializerMethodField()

    class Meta:
        model = ContaFiado
        fields = [
            "id",
            "cliente_id",
            "cliente_nome",
            "cliente_documento",
            "cliente_telefone",
            "cliente_whatsapp",
            "status",
            "valor_total",
            "valor_pago",
            "valor_restante",
            "data_abertura",
            "data_vencimento",
            "dias_atraso",
            "status_cobranca",
            "ultima_cobranca_id",
            "ultima_cobranca_tipo",
            "ultima_cobranca_em",
            "tem_contato",
            "created_at",
            "updated_at",
        ]

    def get_tem_contato(self, obj):
        return bool((obj.cliente.whatsapp or obj.cliente.telefone or "").strip())


class CobrancaPreviewRequestSerializer(serializers.Serializer):
    conta_id = serializers.UUIDField()
    tipo = serializers.ChoiceField(choices=TIPOS_COBRANCA_CHOICES, required=False)


class CobrancaPreviewSerializer(serializers.Serializer):
    conta_id = serializers.UUIDField()
    cliente_id = serializers.UUIDField()
    cliente_nome = serializers.CharField()
    valor = serializers.DecimalField(max_digits=14, decimal_places=2)
    data_vencimento = serializers.DateField(allow_null=True)
    data_vencimento_formatada = serializers.CharField()
    dias_atraso = serializers.IntegerField()
    tipo = serializers.CharField()
    mensagem = serializers.CharField()


class EnviarCobrancaSerializer(CobrancaPreviewRequestSerializer):
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=180)


class EnviarLoteCobrancaSerializer(serializers.Serializer):
    criterio = serializers.ChoiceField(choices=[1, 7, 15, 30])
    conta_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=180)


class ResultadoLoteCobrancaSerializer(serializers.Serializer):
    criterio = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    valor_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    notificacoes = serializers.ListField(child=serializers.UUIDField())
    falhas = serializers.ListField(child=serializers.DictField())


class DashboardCobrancaSerializer(serializers.Serializer):
    pendentes = serializers.IntegerField()
    mensagens_enviadas = serializers.IntegerField()
    entregues = serializers.IntegerField()
    lidas = serializers.IntegerField()
    falharam = serializers.IntegerField()
    taxa_entrega = serializers.FloatField()
    taxa_leitura = serializers.FloatField()
    clientes_cobrados = serializers.IntegerField()
    valor_cobrado = serializers.DecimalField(max_digits=14, decimal_places=2)
    valor_recuperado = serializers.DecimalField(max_digits=14, decimal_places=2)
    percentual_recuperacao = serializers.FloatField()


class TemplatesOperacionaisSerializer(serializers.Serializer):
    criados = serializers.IntegerField()
    templates = serializers.ListField(child=serializers.UUIDField())
