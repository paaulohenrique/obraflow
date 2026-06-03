import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import BaseModel


E164_RE = re.compile(r"^\+\d{7,15}$")


def normalizar_telefone(numero: str) -> str:
    """Converte número brasileiro para E.164 (+55DDNNNNNNNN)."""
    digits = re.sub(r"\D", "", numero)
    if digits.startswith("55") and len(digits) >= 12:
        return f"+{digits}"
    if len(digits) in (10, 11):
        return f"+55{digits}"
    return f"+{digits}"


def validar_telefone_e164(numero: str) -> None:
    normalizado = normalizar_telefone(numero)
    if not E164_RE.match(normalizado):
        raise ValidationError(
            f"Número de telefone inválido: {numero!r}. Esperado formato E.164."
        )


class CanalNotificacao(BaseModel):
    TIPO_WHATSAPP = "WHATSAPP"
    TIPO_EMAIL = "EMAIL"
    TIPO_CHOICES = [
        (TIPO_WHATSAPP, "WhatsApp"),
        (TIPO_EMAIL, "E-mail"),
    ]

    PROVIDER_META_CLOUD = "META_CLOUD"
    PROVIDER_CHOICES = [
        (PROVIDER_META_CLOUD, "Meta Cloud API"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="canais_notificacao",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)
    provider = models.CharField(max_length=40, choices=PROVIDER_CHOICES)
    configuracao = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="canais_notificacao_criados",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Canal de Notificação"
        verbose_name_plural = "Canais de Notificação"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "tipo"],
                condition=Q(ativo=True) & Q(deleted_at__isnull=True),
                name="notif_unique_canal_ativo_tipo_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "tipo", "ativo"]),
            models.Index(fields=["company", "provider"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class TemplateNotificacao(BaseModel):
    TIPO_COBRANCA_FIADO = "COBRANCA_FIADO"
    TIPO_LEMBRETE_VENCIMENTO = "LEMBRETE_VENCIMENTO"
    TIPO_COBRANCA_1_DIA = "COBRANCA_1_DIA"
    TIPO_COBRANCA_7_DIAS = "COBRANCA_7_DIAS"
    TIPO_COBRANCA_15_DIAS = "COBRANCA_15_DIAS"
    TIPO_COBRANCA_30_DIAS = "COBRANCA_30_DIAS"
    TIPO_CONFIRMACAO_PAGAMENTO = "CONFIRMACAO_PAGAMENTO"
    TIPO_AGRADECIMENTO_PAGAMENTO = "AGRADECIMENTO_PAGAMENTO"
    TIPO_RESUMO_CONTA = "RESUMO_CONTA"
    TIPO_AVISO_ATRASO = "AVISO_ATRASO"
    TIPO_CHOICES = [
        (TIPO_COBRANCA_FIADO, "Cobrança de Fiado"),
        (TIPO_LEMBRETE_VENCIMENTO, "Lembrete de Vencimento"),
        (TIPO_COBRANCA_1_DIA, "Cobrança 1 dia após vencimento"),
        (TIPO_COBRANCA_7_DIAS, "Cobrança 7 dias após vencimento"),
        (TIPO_COBRANCA_15_DIAS, "Cobrança 15 dias após vencimento"),
        (TIPO_COBRANCA_30_DIAS, "Cobrança 30 dias após vencimento"),
        (TIPO_CONFIRMACAO_PAGAMENTO, "Confirmação de Pagamento"),
        (TIPO_AGRADECIMENTO_PAGAMENTO, "Agradecimento de Pagamento"),
        (TIPO_RESUMO_CONTA, "Resumo da Conta"),
        (TIPO_AVISO_ATRASO, "Aviso de Conta Atrasada"),
    ]

    CATEGORIA_UTILITY = "UTILITY"
    CATEGORIA_MARKETING = "MARKETING"
    CATEGORIA_AUTHENTICATION = "AUTHENTICATION"
    CATEGORIA_CHOICES = [
        (CATEGORIA_UTILITY, "Utilidade"),
        (CATEGORIA_MARKETING, "Marketing"),
        (CATEGORIA_AUTHENTICATION, "Autenticação"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="templates_notificacao",
    )
    canal = models.ForeignKey(
        CanalNotificacao,
        on_delete=models.PROTECT,
        related_name="templates",
    )
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES)
    provider_template_name = models.CharField(max_length=120, blank=True)
    linguagem = models.CharField(max_length=10, default="pt_BR")
    categoria = models.CharField(
        max_length=20, choices=CATEGORIA_CHOICES, default=CATEGORIA_UTILITY
    )
    corpo = models.TextField(blank=True)
    variaveis = models.JSONField(default=list, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Template de Notificação"
        verbose_name_plural = "Templates de Notificação"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "tipo", "canal"],
                condition=Q(ativo=True) & Q(deleted_at__isnull=True),
                name="notif_unique_template_ativo_tipo_canal",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "tipo", "ativo"]),
            models.Index(fields=["company", "canal", "ativo"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class Notificacao(BaseModel):
    STATUS_PENDENTE = "PENDENTE"
    STATUS_ENFILEIRADA = "ENFILEIRADA"
    STATUS_ENVIADA = "ENVIADA"
    STATUS_ENTREGUE = "ENTREGUE"
    STATUS_LIDA = "LIDA"
    STATUS_FALHOU = "FALHOU"
    STATUS_CANCELADA = "CANCELADA"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_ENFILEIRADA, "Enfileirada"),
        (STATUS_ENVIADA, "Enviada"),
        (STATUS_ENTREGUE, "Entregue"),
        (STATUS_LIDA, "Lida"),
        (STATUS_FALHOU, "Falhou"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    TIPO_COBRANCA_FIADO = "COBRANCA_FIADO"
    TIPO_LEMBRETE_VENCIMENTO = "LEMBRETE_VENCIMENTO"
    TIPO_COBRANCA_1_DIA = "COBRANCA_1_DIA"
    TIPO_COBRANCA_7_DIAS = "COBRANCA_7_DIAS"
    TIPO_COBRANCA_15_DIAS = "COBRANCA_15_DIAS"
    TIPO_COBRANCA_30_DIAS = "COBRANCA_30_DIAS"
    TIPO_CONFIRMACAO_PAGAMENTO = "CONFIRMACAO_PAGAMENTO"
    TIPO_AGRADECIMENTO_PAGAMENTO = "AGRADECIMENTO_PAGAMENTO"
    TIPO_RESUMO_CONTA = "RESUMO_CONTA"
    TIPO_AVISO_ATRASO = "AVISO_ATRASO"
    TIPO_CHOICES = [
        (TIPO_COBRANCA_FIADO, "Cobrança de Fiado"),
        (TIPO_LEMBRETE_VENCIMENTO, "Lembrete de Vencimento"),
        (TIPO_COBRANCA_1_DIA, "Cobrança 1 dia após vencimento"),
        (TIPO_COBRANCA_7_DIAS, "Cobrança 7 dias após vencimento"),
        (TIPO_COBRANCA_15_DIAS, "Cobrança 15 dias após vencimento"),
        (TIPO_COBRANCA_30_DIAS, "Cobrança 30 dias após vencimento"),
        (TIPO_CONFIRMACAO_PAGAMENTO, "Confirmação de Pagamento"),
        (TIPO_AGRADECIMENTO_PAGAMENTO, "Agradecimento de Pagamento"),
        (TIPO_RESUMO_CONTA, "Resumo da Conta"),
        (TIPO_AVISO_ATRASO, "Aviso de Conta Atrasada"),
    ]

    TERMINAL_STATUSES = {STATUS_ENVIADA, STATUS_ENTREGUE, STATUS_LIDA, STATUS_CANCELADA}

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="notificacoes",
    )
    canal = models.ForeignKey(
        CanalNotificacao,
        on_delete=models.PROTECT,
        related_name="notificacoes",
    )
    template = models.ForeignKey(
        TemplateNotificacao,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notificacoes",
    )
    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES)
    destinatario_nome = models.CharField(max_length=255)
    destinatario_contato = models.CharField(max_length=50)
    mensagem = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDENTE
    )
    provider_message_id = models.CharField(max_length=120, blank=True)
    erro_codigo = models.CharField(max_length=80, blank=True)
    erro_mensagem = models.TextField(blank=True)
    origem_tipo = models.CharField(max_length=80, blank=True)
    origem_id = models.UUIDField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=180, blank=True, db_index=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes_criadas",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="notif_unique_idempotency_key_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["company", "tipo", "created_at"]),
            models.Index(fields=["company", "origem_tipo", "origem_id"]),
            models.Index(fields=["company", "destinatario_contato"]),
            models.Index(fields=["company", "created_by", "created_at"]),
            models.Index(fields=["company", "sent_at"]),
        ]

    def __str__(self):
        return f"{self.tipo} → {self.destinatario_contato} ({self.status})"

    @property
    def ja_enviada(self) -> bool:
        return self.status in self.TERMINAL_STATUSES

    @property
    def pode_reenviar(self) -> bool:
        return self.status == self.STATUS_FALHOU


class EventoWebhookWhatsApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="eventos_webhook_whatsapp",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=40, default="META_CLOUD")
    event_type = models.CharField(max_length=80, blank=True)
    provider_message_id = models.CharField(max_length=120, blank=True, db_index=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Evento Webhook WhatsApp"
        verbose_name_plural = "Eventos Webhook WhatsApp"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["provider_message_id", "processed"]),
            models.Index(fields=["received_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} {self.provider_message_id} (processed={self.processed})"
