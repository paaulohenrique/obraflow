from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel

from .services.storage import boleto_upload_path, preview_upload_path


ZERO = Decimal("0.00")


class BoletoOCR(BaseModel):
    STATUS_ENVIADO = "ENVIADO"
    STATUS_PROCESSANDO = "PROCESSANDO"
    STATUS_AGUARDANDO_REVISAO = "AGUARDANDO_REVISAO"
    STATUS_CONFIRMADO = "CONFIRMADO"
    STATUS_REJEITADO = "REJEITADO"
    STATUS_ERRO = "ERRO"
    STATUS_CHOICES = [
        (STATUS_ENVIADO, "Enviado"),
        (STATUS_PROCESSANDO, "Processando"),
        (STATUS_AGUARDANDO_REVISAO, "Aguardando revisão"),
        (STATUS_CONFIRMADO, "Confirmado"),
        (STATUS_REJEITADO, "Rejeitado"),
        (STATUS_ERRO, "Erro"),
    ]

    TIPO_PDF = "PDF"
    TIPO_JPG = "JPG"
    TIPO_JPEG = "JPEG"
    TIPO_PNG = "PNG"
    TIPO_WEBP = "WEBP"
    TIPO_CHOICES = [
        (TIPO_PDF, "PDF"),
        (TIPO_JPG, "JPG"),
        (TIPO_JPEG, "JPEG"),
        (TIPO_PNG, "PNG"),
        (TIPO_WEBP, "WEBP"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="boletos_ocr",
    )
    arquivo = models.FileField(upload_to=boleto_upload_path)
    arquivo_nome_original = models.CharField(max_length=255)
    tipo_arquivo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    content_type = models.CharField(max_length=120)
    tamanho_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, blank=True)
    preview_image = models.ImageField(upload_to=preview_upload_path, null=True, blank=True)
    preview_pages = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_ENVIADO)

    fornecedor = models.ForeignKey(
        "estoque.Fornecedor",
        on_delete=models.PROTECT,
        related_name="boletos_ocr",
        null=True,
        blank=True,
    )
    fornecedor_nome = models.CharField(max_length=300, blank=True)
    documento_beneficiario = models.CharField(max_length=20, blank=True)
    documento_pagador = models.CharField(max_length=20, blank=True)
    banco_codigo = models.CharField(max_length=10, blank=True)
    banco_nome = models.CharField(max_length=120, blank=True)
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    vencimento = models.DateField(null=True, blank=True)
    data_emissao = models.DateField(null=True, blank=True)
    linha_digitavel = models.CharField(max_length=80, blank=True)
    codigo_barras = models.CharField(max_length=60, blank=True)

    texto_ocr = models.TextField(blank=True)
    payload_ocr = models.JSONField(default=dict, blank=True)
    raw_provider_response = models.JSONField(default=dict, blank=True)
    campos_extraidos = models.JSONField(default=dict, blank=True)
    campos_confianca = models.JSONField(default=dict, blank=True)
    confianca_ocr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO), MaxValueValidator(Decimal("100.00"))],
    )

    conta_pagar = models.OneToOneField(
        "financeiro.ContaPagar",
        on_delete=models.PROTECT,
        related_name="boleto_ocr",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="boletos_enviados",
        null=True,
        blank=True,
    )
    processado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="boletos_processados",
        null=True,
        blank=True,
    )
    confirmado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="boletos_confirmados",
        null=True,
        blank=True,
    )
    rejeitado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="boletos_rejeitados",
        null=True,
        blank=True,
    )

    ocr_started_at = models.DateTimeField(null=True, blank=True)
    ocr_finished_at = models.DateTimeField(null=True, blank=True)
    confirmado_at = models.DateTimeField(null=True, blank=True)
    rejeitado_at = models.DateTimeField(null=True, blank=True)
    erro_codigo = models.CharField(max_length=80, blank=True)
    erro_mensagem = models.TextField(blank=True)
    tentativas_ocr = models.PositiveSmallIntegerField(default=0)
    motivo_rejeicao = models.TextField(blank=True)
    observacao = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=140, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Boleto OCR"
        verbose_name_plural = "Boletos OCR"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="boletos_unique_idempotency_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "sha256"],
                condition=Q(deleted_at__isnull=True) & ~Q(sha256=""),
                name="boletos_unique_sha256_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "linha_digitavel"],
                condition=Q(deleted_at__isnull=True) & ~Q(linha_digitavel=""),
                name="boletos_unique_linha_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "codigo_barras"],
                condition=Q(deleted_at__isnull=True) & ~Q(codigo_barras=""),
                name="boletos_unique_codigo_company_active",
            ),
            models.CheckConstraint(
                condition=Q(valor__isnull=True) | Q(valor__gt=0),
                name="boletos_valor_gt_zero_or_null",
            ),
            models.CheckConstraint(
                condition=Q(confianca_ocr__gte=0) & Q(confianca_ocr__lte=100),
                name="boletos_confianca_between_0_100",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["company", "vencimento"]),
            models.Index(fields=["company", "fornecedor", "vencimento"]),
            models.Index(fields=["company", "created_by", "created_at"]),
            models.Index(fields=["company", "conta_pagar"]),
        ]

    def clean(self):
        super().clean()
        self.arquivo_nome_original = (self.arquivo_nome_original or "").strip()
        self.sha256 = (self.sha256 or "").strip().lower()
        self.linha_digitavel = (self.linha_digitavel or "").strip()
        self.codigo_barras = (self.codigo_barras or "").strip()
        self.fornecedor_nome = (self.fornecedor_nome or "").strip()
        self.documento_beneficiario = (self.documento_beneficiario or "").strip()
        self.documento_pagador = (self.documento_pagador or "").strip()
        self.banco_codigo = (self.banco_codigo or "").strip()
        self.banco_nome = (self.banco_nome or "").strip()
        self.erro_codigo = (self.erro_codigo or "").strip()
        self.erro_mensagem = (self.erro_mensagem or "").strip()
        self.motivo_rejeicao = (self.motivo_rejeicao or "").strip()
        self.observacao = (self.observacao or "").strip()
        self.idempotency_key = (self.idempotency_key or "").strip()
        if self.valor is not None and self.valor <= ZERO:
            raise ValidationError({"valor": "Valor deve ser maior que zero."})
        if self.fornecedor_id and self.company_id and self.fornecedor.company_id != self.company_id:
            raise ValidationError({"fornecedor": "Fornecedor não pertence à empresa."})
        if self.conta_pagar_id and self.company_id and self.conta_pagar.company_id != self.company_id:
            raise ValidationError({"conta_pagar": "Conta a pagar não pertence à empresa."})
        if self.status == self.STATUS_CONFIRMADO and not self.conta_pagar_id:
            raise ValidationError({"conta_pagar": "Boleto confirmado exige conta a pagar."})
        if self.status == self.STATUS_REJEITADO and not self.motivo_rejeicao:
            raise ValidationError({"motivo_rejeicao": "Motivo é obrigatório para rejeição."})

    def __str__(self):
        return f"{self.arquivo_nome_original} ({self.status})"


class OCRProcessamento(BaseModel):
    PROVIDER_GOOGLE_VISION = "GOOGLE_VISION"
    PROVIDER_FAKE = "FAKE"
    PROVIDER_CHOICES = [
        (PROVIDER_GOOGLE_VISION, "Google Vision"),
        (PROVIDER_FAKE, "Fake"),
    ]

    STATUS_PROCESSANDO = "PROCESSANDO"
    STATUS_SUCESSO = "SUCESSO"
    STATUS_ERRO = "ERRO"
    STATUS_TIMEOUT = "TIMEOUT"
    STATUS_CHOICES = [
        (STATUS_PROCESSANDO, "Processando"),
        (STATUS_SUCESSO, "Sucesso"),
        (STATUS_ERRO, "Erro"),
        (STATUS_TIMEOUT, "Timeout"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="ocr_processamentos",
    )
    boleto = models.ForeignKey(BoletoOCR, on_delete=models.PROTECT, related_name="processamentos")
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSANDO)
    tentativa = models.PositiveSmallIntegerField()
    task_id = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    texto_extraido = models.TextField(blank=True)
    payload_response = models.JSONField(default=dict, blank=True)
    raw_provider_response = models.JSONField(default=dict, blank=True)
    erro_codigo = models.CharField(max_length=80, blank=True)
    erro_mensagem = models.TextField(blank=True)
    confianca_ocr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO), MaxValueValidator(Decimal("100.00"))],
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Processamento OCR"
        verbose_name_plural = "Processamentos OCR"
        indexes = [
            models.Index(fields=["company", "boleto", "tentativa"]),
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["task_id"]),
        ]

    def clean(self):
        super().clean()
        if self.company_id and self.boleto_id and self.boleto.company_id != self.company_id:
            raise ValidationError({"boleto": "Boleto não pertence à empresa."})

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_update", False):
            raise RuntimeError("Processamento OCR é imutável; use os services de boletos.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Processamento OCR é imutável e não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Processamento OCR é imutável e não pode ser removido.")

    def __str__(self):
        return f"{self.provider} tentativa {self.tentativa} ({self.status})"


class HistoricoBoleto(BaseModel):
    EVENTO_UPLOAD_REALIZADO = "UPLOAD_REALIZADO"
    EVENTO_OCR_INICIADO = "OCR_INICIADO"
    EVENTO_OCR_CONCLUIDO = "OCR_CONCLUIDO"
    EVENTO_OCR_FALHOU = "OCR_FALHOU"
    EVENTO_OCR_REPROCESSADO = "OCR_REPROCESSADO"
    EVENTO_CONFIRMADO = "CONFIRMADO"
    EVENTO_REJEITADO = "REJEITADO"
    EVENTO_CONTA_PAGAR_CRIADA = "CONTA_PAGAR_CRIADA"
    EVENTO_CHOICES = [
        (EVENTO_UPLOAD_REALIZADO, "Upload realizado"),
        (EVENTO_OCR_INICIADO, "OCR iniciado"),
        (EVENTO_OCR_CONCLUIDO, "OCR concluído"),
        (EVENTO_OCR_FALHOU, "OCR falhou"),
        (EVENTO_OCR_REPROCESSADO, "OCR reprocessado"),
        (EVENTO_CONFIRMADO, "Confirmado"),
        (EVENTO_REJEITADO, "Rejeitado"),
        (EVENTO_CONTA_PAGAR_CRIADA, "Conta a pagar criada"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="historicos_boletos",
    )
    boleto = models.ForeignKey(BoletoOCR, on_delete=models.PROTECT, related_name="historicos")
    evento = models.CharField(max_length=40, choices=EVENTO_CHOICES)
    descricao = models.CharField(max_length=255)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="historicos_boletos",
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Histórico de Boleto"
        verbose_name_plural = "Históricos de Boletos"
        indexes = [
            models.Index(fields=["company", "boleto", "created_at"]),
            models.Index(fields=["company", "evento", "created_at"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def clean(self):
        super().clean()
        if self.company_id and self.boleto_id and self.boleto.company_id != self.company_id:
            raise ValidationError({"boleto": "Boleto não pertence à empresa."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Histórico de boleto é imutável.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Histórico de boleto é imutável e não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Histórico de boleto é imutável e não pode ser removido.")

    def __str__(self):
        return f"{self.evento} {self.boleto_id}"
