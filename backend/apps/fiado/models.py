from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import BaseModel


ZERO_MONEY = Decimal("0.00")
ZERO_QTY = Decimal("0.000")
MIN_QTY = Decimal("0.001")


def money(value: Decimal | None) -> Decimal:
    return (value or ZERO_MONEY).quantize(Decimal("0.01"))


def item_subtotal(*, quantidade: Decimal, preco_unitario: Decimal) -> Decimal:
    return money(quantidade * preco_unitario)


def item_quantidade_precificada(
    *,
    quantidade: Decimal,
    quantidade_informada: Decimal | None = None,
    tem_forma_venda: bool = False,
) -> Decimal:
    if tem_forma_venda and quantidade_informada is not None:
        return quantidade_informada
    return quantidade


class NoBulkMutationQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Registros do fiado devem ser alterados via services.")

    def delete(self):
        raise RuntimeError("Registros do fiado não podem ser removidos fisicamente.")


class NoBulkMutationManager(models.Manager):
    def get_queryset(self):
        return NoBulkMutationQuerySet(self.model, using=self._db)


class ContaFiado(BaseModel):
    STATUS_ABERTA = "ABERTA"
    STATUS_FECHADA = "FECHADA"
    STATUS_CANCELADA = "CANCELADA"
    STATUS_CHOICES = [
        (STATUS_ABERTA, "Aberta"),
        (STATUS_FECHADA, "Fechada"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="contas_fiado",
    )
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="contas_fiado",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTA)
    valor_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    valor_pago = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    valor_restante = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    data_abertura = models.DateTimeField(default=timezone.now)
    data_vencimento = models.DateField(null=True, blank=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    observacao = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="contas_fiado_criadas",
        null=True,
        blank=True,
    )
    closed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="contas_fiado_fechadas",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="contas_fiado_canceladas",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Conta Fiado"
        verbose_name_plural = "Contas Fiado"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "cliente"],
                condition=Q(status="ABERTA") & Q(deleted_at__isnull=True),
                name="fiado_unique_conta_aberta_cliente_company",
            ),
            models.CheckConstraint(
                condition=Q(valor_total__gte=0),
                name="fiado_conta_valor_total_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_pago__gte=0),
                name="fiado_conta_valor_pago_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_restante__gte=0),
                name="fiado_conta_valor_restante_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "cliente", "status"]),
            models.Index(fields=["company", "status", "data_vencimento"]),
            models.Index(fields=["company", "cliente", "created_at"]),
            models.Index(fields=["company", "created_by", "created_at"]),
            models.Index(fields=["company", "valor_restante"]),
        ]

    def clean(self):
        super().clean()
        self.observacao = (self.observacao or "").strip()
        self.motivo_cancelamento = (self.motivo_cancelamento or "").strip()
        self.valor_total = money(self.valor_total)
        self.valor_pago = money(self.valor_pago)
        self.valor_restante = money(self.valor_restante)
        if self.valor_restante != money(self.valor_total - self.valor_pago):
            raise ValidationError({
                "valor_restante": "Valor restante deve ser valor_total - valor_pago."
            })

    @property
    def is_parcial(self) -> bool:
        return (
            self.status == self.STATUS_ABERTA
            and self.valor_pago > ZERO_MONEY
            and self.valor_restante > ZERO_MONEY
        )

    @property
    def is_atrasada(self) -> bool:
        return (
            self.status == self.STATUS_ABERTA
            and self.data_vencimento is not None
            and self.data_vencimento < timezone.localdate()
            and self.valor_restante > ZERO_MONEY
        )

    @property
    def dias_atraso(self) -> int:
        if not self.is_atrasada:
            return 0
        return (timezone.localdate() - self.data_vencimento).days

    def delete(self, *args, **kwargs):
        raise RuntimeError("Conta fiado não pode ser removida fisicamente.")

    def __str__(self):
        return f"Fiado {self.cliente} - {self.status} ({self.valor_restante})"


class ItemFiado(BaseModel):
    STATUS_ATIVO = "ATIVO"
    STATUS_CANCELADO = "CANCELADO"
    STATUS_CHOICES = [
        (STATUS_ATIVO, "Ativo"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    objects = NoBulkMutationManager()

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="itens_fiado",
    )
    conta = models.ForeignKey(
        ContaFiado,
        on_delete=models.PROTECT,
        related_name="itens",
    )
    produto = models.ForeignKey(
        "estoque.Produto",
        on_delete=models.PROTECT,
        related_name="itens_fiado",
    )
    forma_venda = models.ForeignKey(
        "estoque.FormaVendaProduto",
        on_delete=models.SET_NULL,
        related_name="itens_fiado",
        null=True,
        blank=True,
    )
    quantidade_informada = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        null=True,
        blank=True,
    )
    quantidade = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(MIN_QTY)],
    )
    preco_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    data_lancamento = models.DateTimeField(default=timezone.now)
    movimentacao_estoque = models.ForeignKey(
        "estoque.MovimentacaoEstoque",
        on_delete=models.PROTECT,
        related_name="itens_fiado_origem",
        null=True,
        blank=True,
    )
    movimentacao_cancelamento = models.ForeignKey(
        "estoque.MovimentacaoEstoque",
        on_delete=models.PROTECT,
        related_name="itens_fiado_cancelamento",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ATIVO)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="itens_fiado_criados",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="itens_fiado_cancelados",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)
    observacao = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Item Fiado"
        verbose_name_plural = "Itens Fiado"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="fiado_unique_item_key_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "movimentacao_estoque"],
                condition=Q(deleted_at__isnull=True) & Q(movimentacao_estoque__isnull=False),
                name="fiado_unique_item_mov_saida_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "movimentacao_cancelamento"],
                condition=Q(deleted_at__isnull=True) & Q(movimentacao_cancelamento__isnull=False),
                name="fiado_unique_item_mov_cancel_company_active",
            ),
            models.CheckConstraint(
                condition=Q(quantidade__gt=0),
                name="fiado_item_quantidade_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(preco_unitario__gte=0),
                name="fiado_item_preco_unitario_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="fiado_item_subtotal_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "conta", "status"]),
            models.Index(fields=["company", "produto", "created_at"]),
            models.Index(fields=["company", "created_by", "created_at"]),
            models.Index(fields=["company", "idempotency_key"]),
        ]

    def clean(self):
        super().clean()
        self.observacao = (self.observacao or "").strip()
        self.motivo_cancelamento = (self.motivo_cancelamento or "").strip()
        self.idempotency_key = (self.idempotency_key or "").strip()
        if self.quantidade <= ZERO_QTY:
            raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})
        self.preco_unitario = money(self.preco_unitario)
        quantidade_precificada = item_quantidade_precificada(
            quantidade=self.quantidade,
            quantidade_informada=self.quantidade_informada,
            tem_forma_venda=bool(self.forma_venda_id),
        )
        self.subtotal = item_subtotal(
            quantidade=quantidade_precificada,
            preco_unitario=self.preco_unitario,
        )

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_update", False):
            raise RuntimeError("Item fiado é imutável; use os services de fiado.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Item fiado não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Item fiado não pode ser removido.")

    def __str__(self):
        return f"{self.produto} x {self.quantidade} ({self.status})"


class PagamentoFiado(BaseModel):
    STATUS_CONFIRMADO = "CONFIRMADO"
    STATUS_CANCELADO = "CANCELADO"
    STATUS_CHOICES = [
        (STATUS_CONFIRMADO, "Confirmado"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    FORMA_DINHEIRO = "DINHEIRO"
    FORMA_PIX = "PIX"
    FORMA_CARTAO = "CARTAO"
    FORMA_BOLETO = "BOLETO"
    FORMA_TRANSFERENCIA = "TRANSFERENCIA"
    FORMA_OUTRO = "OUTRO"
    FORMA_CHOICES = [
        (FORMA_DINHEIRO, "Dinheiro"),
        (FORMA_PIX, "PIX"),
        (FORMA_CARTAO, "Cartão"),
        (FORMA_BOLETO, "Boleto"),
        (FORMA_TRANSFERENCIA, "Transferência"),
        (FORMA_OUTRO, "Outro"),
    ]

    objects = NoBulkMutationManager()

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="pagamentos_fiado",
    )
    conta = models.ForeignKey(
        ContaFiado,
        on_delete=models.PROTECT,
        related_name="pagamentos",
    )
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_CHOICES)
    data_pagamento = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMADO)
    observacao = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="pagamentos_fiado_criados",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="pagamentos_fiado_cancelados",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Pagamento Fiado"
        verbose_name_plural = "Pagamentos Fiado"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="fiado_unique_pagamento_key_company_active",
            ),
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="fiado_pagamento_valor_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "conta", "status"]),
            models.Index(fields=["company", "forma_pagamento", "data_pagamento"]),
            models.Index(fields=["company", "created_by", "created_at"]),
            models.Index(fields=["company", "idempotency_key"]),
        ]

    def clean(self):
        super().clean()
        self.valor = money(self.valor)
        if self.valor <= ZERO_MONEY:
            raise ValidationError({"valor": "Valor deve ser maior que zero."})
        self.observacao = (self.observacao or "").strip()
        self.motivo_cancelamento = (self.motivo_cancelamento or "").strip()
        self.idempotency_key = (self.idempotency_key or "").strip()

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_update", False):
            raise RuntimeError("Pagamento fiado é imutável; use os services de fiado.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Pagamento fiado não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Pagamento fiado não pode ser removido.")

    def __str__(self):
        return f"{self.valor} {self.forma_pagamento} ({self.status})"


class HistoricoFiado(BaseModel):
    EVENTO_CONTA_CRIADA = "CONTA_CRIADA"
    EVENTO_ITEM_ADICIONADO = "ITEM_ADICIONADO"
    EVENTO_ITEM_CANCELADO = "ITEM_CANCELADO"
    EVENTO_PAGAMENTO_REGISTRADO = "PAGAMENTO_REGISTRADO"
    EVENTO_PAGAMENTO_CANCELADO = "PAGAMENTO_CANCELADO"
    EVENTO_CONTA_FECHADA = "CONTA_FECHADA"
    EVENTO_CONTA_CANCELADA = "CONTA_CANCELADA"
    EVENTO_VENCIMENTO_ALTERADO = "VENCIMENTO_ALTERADO"
    EVENTO_OBSERVACAO_ALTERADA = "OBSERVACAO_ALTERADA"
    EVENTO_COBRANCA_ENVIADA = "COBRANCA_ENVIADA"
    EVENTO_COBRANCA_ENTREGUE = "COBRANCA_ENTREGUE"
    EVENTO_COBRANCA_LIDA = "COBRANCA_LIDA"
    EVENTO_COBRANCA_FALHOU = "COBRANCA_FALHOU"
    EVENTO_CHOICES = [
        (EVENTO_CONTA_CRIADA, "Conta criada"),
        (EVENTO_ITEM_ADICIONADO, "Item adicionado"),
        (EVENTO_ITEM_CANCELADO, "Item cancelado"),
        (EVENTO_PAGAMENTO_REGISTRADO, "Pagamento registrado"),
        (EVENTO_PAGAMENTO_CANCELADO, "Pagamento cancelado"),
        (EVENTO_CONTA_FECHADA, "Conta fechada"),
        (EVENTO_CONTA_CANCELADA, "Conta cancelada"),
        (EVENTO_VENCIMENTO_ALTERADO, "Vencimento alterado"),
        (EVENTO_OBSERVACAO_ALTERADA, "Observação alterada"),
        (EVENTO_COBRANCA_ENVIADA, "Cobrança enviada"),
        (EVENTO_COBRANCA_ENTREGUE, "Cobrança entregue"),
        (EVENTO_COBRANCA_LIDA, "Cobrança lida"),
        (EVENTO_COBRANCA_FALHOU, "Cobrança falhou"),
    ]

    objects = NoBulkMutationManager()

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="historicos_fiado",
    )
    conta = models.ForeignKey(
        ContaFiado,
        on_delete=models.PROTECT,
        related_name="historico",
    )
    item = models.ForeignKey(
        ItemFiado,
        on_delete=models.PROTECT,
        related_name="historico",
        null=True,
        blank=True,
    )
    pagamento = models.ForeignKey(
        PagamentoFiado,
        on_delete=models.PROTECT,
        related_name="historico",
        null=True,
        blank=True,
    )
    evento = models.CharField(max_length=40, choices=EVENTO_CHOICES)
    descricao = models.TextField()
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="historicos_fiado",
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Histórico Fiado"
        verbose_name_plural = "Históricos Fiado"
        indexes = [
            models.Index(fields=["company", "conta", "created_at"]),
            models.Index(fields=["company", "evento", "created_at"]),
            models.Index(fields=["company", "created_by", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Histórico de fiado é imutável.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Histórico de fiado é imutável.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Histórico de fiado é imutável.")

    def __str__(self):
        return f"{self.evento} - {self.conta_id}"
