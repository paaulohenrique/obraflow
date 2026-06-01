from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import BaseModel
from apps.empresas.validators import clean_cnpj


ZERO = Decimal("0.00")


def _nfe_xml_upload_path(instance, filename):
    return f"notas_entrada/{instance.company_id}/{filename}"


class NotaFiscalEntrada(BaseModel):
    # ── Status ──────────────────────────────────────────────────────────────────
    STATUS_AGUARDANDO_REVISAO = "AGUARDANDO_REVISAO"
    STATUS_CONFIRMADA = "CONFIRMADA"
    STATUS_REJEITADA = "REJEITADA"
    STATUS_IMPORTADA = "IMPORTADA"
    STATUS_PROCESSANDO = "PROCESSANDO"
    STATUS_ERRO = "ERRO"
    STATUS_CHOICES = [
        (STATUS_AGUARDANDO_REVISAO, "Aguardando Revisão"),
        (STATUS_CONFIRMADA, "Confirmada"),
        (STATUS_REJEITADA, "Rejeitada"),
        (STATUS_IMPORTADA, "Importada"),
        (STATUS_PROCESSANDO, "Processando"),
        (STATUS_ERRO, "Erro"),
    ]

    # ── Tenant ──────────────────────────────────────────────────────────────────
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="notas_entrada",
    )

    # ── Fornecedor ──────────────────────────────────────────────────────────────
    fornecedor = models.ForeignKey(
        "estoque.Fornecedor",
        on_delete=models.PROTECT,
        related_name="notas_entrada",
        null=True,
        blank=True,
    )
    fornecedor_nome_xml = models.CharField(max_length=300, blank=True)
    fornecedor_cnpj_xml = models.CharField(max_length=14, blank=True)

    # ── Vínculo futuro com Boleto ────────────────────────────────────────────────
    boleto = models.OneToOneField(
        "boletos.BoletoOCR",
        on_delete=models.PROTECT,
        related_name="nota_entrada",
        null=True,
        blank=True,
    )

    # ── Identificação da NF-e ────────────────────────────────────────────────────
    sha256 = models.CharField(max_length=64, blank=True)
    chave_acesso = models.CharField(max_length=44, blank=True)
    numero = models.CharField(max_length=15)
    serie = models.CharField(max_length=3)
    modelo = models.CharField(max_length=2, default="55")
    data_emissao = models.DateField()
    data_entrada = models.DateField(null=True, blank=True)

    # ── Valores Fiscais ──────────────────────────────────────────────────────────
    valor_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    valor_produtos = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    valor_frete = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    valor_desconto = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    valor_icms = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    valor_ipi = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )

    # ── Arquivo XML ──────────────────────────────────────────────────────────────
    xml_file = models.FileField(
        upload_to=_nfe_xml_upload_path, null=True, blank=True
    )

    # ── Status e Financeiro ──────────────────────────────────────────────────────
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_AGUARDANDO_REVISAO)
    conta_pagar = models.OneToOneField(
        "financeiro.ContaPagar",
        on_delete=models.PROTECT,
        related_name="nota_entrada",
        null=True,
        blank=True,
    )

    # ── Payload Extraído ─────────────────────────────────────────────────────────
    payload_extraido = models.JSONField(default=dict, blank=True)

    # ── Rastreabilidade ──────────────────────────────────────────────────────────
    criado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="notas_entrada_criadas",
        null=True,
        blank=True,
    )
    confirmado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="notas_entrada_confirmadas",
        null=True,
        blank=True,
    )
    confirmado_em = models.DateTimeField(null=True, blank=True)
    rejeitado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="notas_entrada_rejeitadas",
        null=True,
        blank=True,
    )
    rejeitado_em = models.DateTimeField(null=True, blank=True)
    motivo_rejeicao = models.TextField(blank=True)

    # ── Erros ────────────────────────────────────────────────────────────────────
    erro_codigo = models.CharField(max_length=80, blank=True)
    erro_mensagem = models.TextField(blank=True)

    # ── Misc ─────────────────────────────────────────────────────────────────────
    observacao = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=140, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Nota Fiscal de Entrada"
        verbose_name_plural = "Notas Fiscais de Entrada"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "chave_acesso"],
                condition=Q(deleted_at__isnull=True) & ~Q(chave_acesso=""),
                name="notas_entrada_unique_chave_acesso_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "sha256"],
                condition=Q(deleted_at__isnull=True) & ~Q(sha256=""),
                name="notas_entrada_unique_sha256_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="notas_entrada_unique_idempotency_company_active",
            ),
            models.CheckConstraint(
                condition=Q(valor_total__gte=0),
                name="notas_entrada_valor_total_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_produtos__gte=0),
                name="notas_entrada_valor_produtos_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["company", "fornecedor", "data_emissao"]),
            models.Index(fields=["company", "data_emissao"]),
            models.Index(fields=["company", "chave_acesso"]),
            models.Index(fields=["company", "sha256"]),
            models.Index(fields=["company", "criado_por", "created_at"]),
            models.Index(fields=["company", "conta_pagar"]),
            models.Index(fields=["company", "fornecedor_cnpj_xml"]),
        ]

    def clean(self):
        super().clean()
        self.numero = (self.numero or "").strip()
        self.serie = (self.serie or "").strip()
        self.modelo = (self.modelo or "").strip()
        self.chave_acesso = (self.chave_acesso or "").strip()
        self.sha256 = (self.sha256 or "").strip().lower()
        self.fornecedor_nome_xml = (self.fornecedor_nome_xml or "").strip()
        self.fornecedor_cnpj_xml = (self.fornecedor_cnpj_xml or "").strip()
        self.idempotency_key = (self.idempotency_key or "").strip()
        self.motivo_rejeicao = (self.motivo_rejeicao or "").strip()
        self.observacao = (self.observacao or "").strip()

        if self.fornecedor_id and self.company_id:
            if self.fornecedor.company_id != self.company_id:
                raise ValidationError({"fornecedor": "Fornecedor não pertence à empresa."})
        if self.conta_pagar_id and self.company_id:
            if self.conta_pagar.company_id != self.company_id:
                raise ValidationError({"conta_pagar": "Conta a pagar não pertence à empresa."})
        if self.boleto_id and self.company_id:
            if self.boleto.company_id != self.company_id:
                raise ValidationError({"boleto": "Boleto não pertence à empresa."})
        if self.status == self.STATUS_REJEITADA and not self.motivo_rejeicao:
            raise ValidationError({"motivo_rejeicao": "Motivo é obrigatório para rejeição."})

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_update", False):
            allowed_fields = {"status", "confirmado_por", "confirmado_em", "rejeitado_por",
                              "rejeitado_em", "motivo_rejeicao", "fornecedor", "conta_pagar",
                              "updated_at", "deleted_at", "is_active", "erro_codigo", "erro_mensagem"}
            update_fields = set(kwargs.get("update_fields", []) or [])
            if update_fields and not update_fields.issubset(allowed_fields):
                forbidden = update_fields - allowed_fields
                raise RuntimeError(
                    f"Nota confirmada/rejeitada não pode alterar campos: {forbidden}"
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Nota fiscal de entrada não pode ser removida fisicamente.")

    def __str__(self):
        return f"NF-e {self.numero}/{self.serie} ({self.status})"


class ItemNotaFiscalEntrada(BaseModel):
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="itens_nota_entrada",
    )
    nota = models.ForeignKey(
        NotaFiscalEntrada,
        on_delete=models.PROTECT,
        related_name="itens",
    )
    produto = models.ForeignKey(
        "estoque.Produto",
        on_delete=models.PROTECT,
        related_name="itens_nota_entrada",
        null=True,
        blank=True,
    )
    forma_venda = models.ForeignKey(
        "estoque.FormaVendaProduto",
        on_delete=models.SET_NULL,
        related_name="itens_nota_entrada",
        null=True,
        blank=True,
    )
    quantidade_informada = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        null=True,
        blank=True,
    )
    descricao_original = models.CharField(max_length=500)
    codigo_fornecedor = models.CharField(max_length=80, blank=True)
    codigo_barras = models.CharField(max_length=80, blank=True)
    ncm = models.CharField(max_length=10, blank=True)
    cfop = models.CharField(max_length=5, blank=True)
    unidade = models.CharField(max_length=10)
    quantidade = models.DecimalField(max_digits=14, decimal_places=3)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=4)
    valor_total_item = models.DecimalField(max_digits=14, decimal_places=2)
    custo_unitario = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    valor_ipi_item = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    valor_icms_item = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    movimentacao_estoque = models.OneToOneField(
        "estoque.MovimentacaoEstoque",
        on_delete=models.PROTECT,
        related_name="item_nota_entrada",
        null=True,
        blank=True,
    )
    ignorado = models.BooleanField(default=False)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = "Item de Nota Fiscal de Entrada"
        verbose_name_plural = "Itens de Nota Fiscal de Entrada"
        ordering = ["ordem"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantidade__gt=0),
                name="notas_entrada_item_quantidade_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_unitario__gte=0),
                name="notas_entrada_item_valor_unitario_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_total_item__gte=0),
                name="notas_entrada_item_valor_total_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "nota", "ordem"]),
            models.Index(fields=["company", "produto"]),
            models.Index(fields=["company", "codigo_barras"]),
            models.Index(fields=["company", "nota", "ignorado"]),
        ]

    def clean(self):
        super().clean()
        self.descricao_original = (self.descricao_original or "").strip()
        self.codigo_fornecedor = (self.codigo_fornecedor or "").strip()
        self.codigo_barras = (self.codigo_barras or "").strip()
        self.ncm = (self.ncm or "").strip()
        self.cfop = (self.cfop or "").strip()
        self.unidade = (self.unidade or "").strip().upper()

        if self.nota_id and self.company_id and self.nota.company_id != self.company_id:
            raise ValidationError({"nota": "Nota não pertence à empresa."})
        if self.produto_id and self.company_id and self.produto.company_id != self.company_id:
            raise ValidationError({"produto": "Produto não pertence à empresa."})
        if self.movimentacao_estoque_id and self.company_id:
            if self.movimentacao_estoque.company_id != self.company_id:
                raise ValidationError({"movimentacao_estoque": "Movimentação não pertence à empresa."})
        if self.ignorado and self.movimentacao_estoque_id:
            raise ValidationError({"ignorado": "Item ignorado não pode ter movimentação de estoque."})

    def __str__(self):
        return f"{self.descricao_original} x{self.quantidade}"


class HistoricoNotaFiscalEntrada(BaseModel):
    EVENTO_XML_IMPORTADO = "XML_IMPORTADO"
    EVENTO_FORNECEDOR_VINCULADO = "FORNECEDOR_VINCULADO"
    EVENTO_ITEM_PRODUTO_VINCULADO = "ITEM_PRODUTO_VINCULADO"
    EVENTO_ITEM_IGNORADO = "ITEM_IGNORADO"
    EVENTO_CONFIRMADA = "CONFIRMADA"
    EVENTO_ENTRADA_ESTOQUE_CRIADA = "ENTRADA_ESTOQUE_CRIADA"
    EVENTO_CONTA_PAGAR_CRIADA = "CONTA_PAGAR_CRIADA"
    EVENTO_REJEITADA = "REJEITADA"
    EVENTO_CHOICES = [
        (EVENTO_XML_IMPORTADO, "XML Importado"),
        (EVENTO_FORNECEDOR_VINCULADO, "Fornecedor Vinculado"),
        (EVENTO_ITEM_PRODUTO_VINCULADO, "Produto Vinculado ao Item"),
        (EVENTO_ITEM_IGNORADO, "Item Ignorado"),
        (EVENTO_CONFIRMADA, "Nota Confirmada"),
        (EVENTO_ENTRADA_ESTOQUE_CRIADA, "Entrada de Estoque Criada"),
        (EVENTO_CONTA_PAGAR_CRIADA, "Conta a Pagar Criada"),
        (EVENTO_REJEITADA, "Nota Rejeitada"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="historicos_nota_entrada",
    )
    nota = models.ForeignKey(
        NotaFiscalEntrada,
        on_delete=models.PROTECT,
        related_name="historicos",
    )
    evento = models.CharField(max_length=40, choices=EVENTO_CHOICES)
    descricao = models.CharField(max_length=255)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="historicos_nota_entrada",
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Histórico de Nota Fiscal de Entrada"
        verbose_name_plural = "Históricos de Notas Fiscais de Entrada"
        indexes = [
            models.Index(fields=["company", "nota", "created_at"]),
            models.Index(fields=["company", "evento", "created_at"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def clean(self):
        super().clean()
        if self.nota_id and self.company_id and self.nota.company_id != self.company_id:
            raise ValidationError({"nota": "Nota não pertence à empresa."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Histórico de nota fiscal é imutável.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Histórico de nota fiscal é imutável e não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Histórico de nota fiscal é imutável e não pode ser removido.")

    def __str__(self):
        return f"{self.evento} — {self.nota_id}"
