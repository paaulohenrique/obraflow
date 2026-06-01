from rest_framework import serializers

from apps.core.serializers import BaseModelSerializer

from .models import CanalNotificacao, Notificacao, TemplateNotificacao


class CanalNotificacaoSerializer(BaseModelSerializer):
    class Meta:
        model = CanalNotificacao
        fields = [
            "id",
            "tipo",
            "nome",
            "ativo",
            "provider",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_active"]

    def validate(self, attrs):
        # nunca aceitar configuracao via API — gerenciado internamente
        attrs.pop("configuracao", None)
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["company"] = self.context["request"].user.company
        return super().create(validated_data)


class CanalNotificacaoWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CanalNotificacao
        fields = ["tipo", "nome", "ativo", "provider"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["company"] = request.user.company
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class TemplateNotificacaoSerializer(BaseModelSerializer):
    class Meta:
        model = TemplateNotificacao
        fields = [
            "id",
            "canal",
            "nome",
            "tipo",
            "provider_template_name",
            "linguagem",
            "categoria",
            "corpo",
            "variaveis",
            "ativo",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_active"]

    def validate_canal(self, canal):
        request = self.context["request"]
        if canal.company_id != request.user.company_id:
            raise serializers.ValidationError("Canal não pertence a esta empresa.")
        return canal

    def create(self, validated_data):
        validated_data["company"] = self.context["request"].user.company
        return super().create(validated_data)


class NotificacaoSerializer(BaseModelSerializer):
    canal_nome = serializers.CharField(source="canal.nome", read_only=True)
    template_nome = serializers.CharField(
        source="template.nome", read_only=True, allow_null=True
    )

    class Meta:
        model = Notificacao
        fields = [
            "id",
            "canal",
            "canal_nome",
            "template",
            "template_nome",
            "tipo",
            "destinatario_nome",
            "destinatario_contato",
            "mensagem",
            "status",
            "provider_message_id",
            "erro_codigo",
            "erro_mensagem",
            "origem_tipo",
            "origem_id",
            "scheduled_at",
            "sent_at",
            "delivered_at",
            "read_at",
            "failed_at",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "canal_nome",
            "template_nome",
            "status",
            "provider_message_id",
            "erro_codigo",
            "erro_mensagem",
            "sent_at",
            "delivered_at",
            "read_at",
            "failed_at",
            "created_at",
            "updated_at",
            "is_active",
        ]


class EnviarCobrancaFiadoSerializer(serializers.Serializer):
    conta_fiado_id = serializers.UUIDField()


class EnviarConfirmacaoPagamentoSerializer(serializers.Serializer):
    pagamento_fiado_id = serializers.UUIDField()


class DashboardSerializer(serializers.Serializer):
    notificacoes_pendentes = serializers.IntegerField()
    enviadas_hoje = serializers.IntegerField()
    entregues_hoje = serializers.IntegerField()
    lidas_hoje = serializers.IntegerField()
    falhas_hoje = serializers.IntegerField()
    taxa_entrega = serializers.FloatField()
    taxa_leitura = serializers.FloatField()
