from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import BaseModel


ZERO_MONEY = Decimal("0.00")
ONE_CENT = Decimal("0.01")


def money(value: Decimal | None) -> Decimal:
    return (value or ZERO_MONEY).quantize(Decimal("0.01"))


class NoBulkMutationQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Registros financeiros devem ser alterados via services.")

    def delete(self):
        raise RuntimeError("Registros financeiros não podem ser removidos fisicamente.")


class NoBulkMutationManager(models.Manager):
    def get_queryset(self):
        return NoBulkMutationQuerySet(self.model, using=self._db)


class ContaFinanceira(BaseModel):
    TIPO_CAIXA = "CAIXA"
    TIPO_BANCO = "BANCO"
    TIPO_CARTEIRA = "CARTEIRA"
    TIPO_OUTRO = "OUTRO"
    TIPO_CHOICES = [
        (TIPO_CAIXA, "Caixa"),
        (TIPO_BANCO, "Banco"),
        (TIPO_CARTEIRA, "Carteira"),
        (TIPO_OUTRO, "Outro"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="contas_financeiras",
    )
    nome = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    saldo_atual = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    ativo = models.BooleanField(default=True)
    observacao = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Conta Financeira"
        verbose_name_plural = "Contas Financeiras"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "nome"],
                condition=Q(deleted_at__isnull=True),
                name="financeiro_unique_conta_nome_company_active",
            ),
            models.CheckConstraint(
                condition=Q(saldo_atual__gte=0),
                name="financeiro_conta_saldo_atual_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "nome"]),
            models.Index(fields=["company", "tipo"]),
            models.Index(fields=["company", "ativo"]),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        self.observacao = (self.observacao or "").strip()
        self.saldo_atual = money(self.saldo_atual)

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_saldo_update", False):
            previous = ContaFinanceira.objects.filter(pk=self.pk).only("saldo_atual").first()
            if previous and money(previous.saldo_atual) != money(self.saldo_atual):
                raise RuntimeError("saldo_atual deve ser alterado apenas via services financeiros.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Conta financeira não pode ser removida fisicamente.")

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class CategoriaFinanceira(BaseModel):
    TIPO_RECEITA = "RECEITA"
    TIPO_DESPESA = "DESPESA"
    TIPO_CHOICES = [
        (TIPO_RECEITA, "Receita"),
        (TIPO_DESPESA, "Despesa"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="categorias_financeiras",
    )
    nome = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField(blank=True)
    ativa = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Categoria Financeira"
        verbose_name_plural = "Categorias Financeiras"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "nome", "tipo"],
                condition=Q(deleted_at__isnull=True),
                name="financeiro_unique_categoria_nome_tipo_company_active",
            )
        ]
        indexes = [
            models.Index(fields=["company", "nome"]),
            models.Index(fields=["company", "tipo"]),
            models.Index(fields=["company", "ativa"]),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        self.descricao = (self.descricao or "").strip()

    def delete(self, *args, **kwargs):
        raise RuntimeError("Categoria financeira não pode ser removida fisicamente.")

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class LancamentoFinanceiro(BaseModel):
    TIPO_ENTRADA = "ENTRADA"
    TIPO_SAIDA = "SAIDA"
    TIPO_CHOICES = [
        (TIPO_ENTRADA, "Entrada"),
        (TIPO_SAIDA, "Saída"),
    ]

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

    ORIGEM_MANUAL = "MANUAL"
    ORIGEM_FIADO = "FIADO"
    ORIGEM_CONTA_PAGAR = "CONTA_PAGAR"
    ORIGEM_ESTORNO = "ESTORNO"
    ORIGEM_AJUSTE = "AJUSTE"
    ORIGEM_CHOICES = [
        (ORIGEM_MANUAL, "Manual"),
        (ORIGEM_FIADO, "Fiado"),
        (ORIGEM_CONTA_PAGAR, "Conta a pagar"),
        (ORIGEM_ESTORNO, "Estorno"),
        (ORIGEM_AJUSTE, "Ajuste"),
    ]

    objects = NoBulkMutationManager()

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="lancamentos_financeiros",
    )
    conta_financeira = models.ForeignKey(
        ContaFinanceira,
        on_delete=models.PROTECT,
        related_name="lancamentos",
    )
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name="lancamentos",
    )
    caixa_diario = models.ForeignKey(
        "financeiro.CaixaDiario",
        on_delete=models.PROTECT,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(ONE_CENT)],
    )
    data_lancamento = models.DateTimeField(default=timezone.now)
    descricao = models.TextField(blank=True)
    origem_tipo = models.CharField(max_length=30, choices=ORIGEM_CHOICES, default=ORIGEM_MANUAL)
    origem_id = models.UUIDField(null=True, blank=True)
    forma_pagamento = models.CharField(
        max_length=20,
        choices=FORMA_CHOICES,
        default=FORMA_OUTRO,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMADO)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="lancamentos_financeiros_criados",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="lancamentos_financeiros_cancelados",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)
    estorno_de = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="estornos",
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(max_length=140, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="financeiro_unique_lancamento_key_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "estorno_de"],
                condition=Q(deleted_at__isnull=True) & Q(estorno_de__isnull=False),
                name="financeiro_unique_estorno_lancamento_company_active",
            ),
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="financeiro_lancamento_valor_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "tipo"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "data_lancamento"]),
            models.Index(fields=["company", "origem_tipo", "origem_id"]),
            models.Index(fields=["company", "idempotency_key"]),
        ]

    def clean(self):
        super().clean()
        self.valor = money(self.valor)
        self.descricao = (self.descricao or "").strip()
        self.motivo_cancelamento = (self.motivo_cancelamento or "").strip()
        self.idempotency_key = (self.idempotency_key or "").strip()
        if self.valor <= ZERO_MONEY:
            raise ValidationError({"valor": "Valor deve ser maior que zero."})
        if self.categoria_id and self.tipo:
            if self.tipo == self.TIPO_ENTRADA and self.categoria.tipo != CategoriaFinanceira.TIPO_RECEITA:
                raise ValidationError({"categoria": "Entrada exige categoria de receita."})
            if self.tipo == self.TIPO_SAIDA and self.categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
                raise ValidationError({"categoria": "Saída exige categoria de despesa."})
        if self.conta_financeira_id and self.company_id:
            if self.conta_financeira.company_id != self.company_id:
                raise ValidationError({"conta_financeira": "Conta não pertence à empresa."})
        if self.categoria_id and self.company_id and self.categoria.company_id != self.company_id:
            raise ValidationError({"categoria": "Categoria não pertence à empresa."})
        if self.caixa_diario_id and self.company_id and self.caixa_diario.company_id != self.company_id:
            raise ValidationError({"caixa_diario": "Caixa não pertence à empresa."})
        if self.estorno_de_id and self.company_id and self.estorno_de.company_id != self.company_id:
            raise ValidationError({"estorno_de": "Lançamento estornado não pertence à empresa."})

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_update", False):
            raise RuntimeError("Lançamento financeiro é imutável; use os services financeiros.")
        super().save(*args, **kwargs)

    def soft_delete(self):
        raise RuntimeError("Lançamento financeiro não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Lançamento financeiro não pode ser removido.")

    def __str__(self):
        return f"{self.tipo} {self.valor} ({self.status})"


class ContaPagar(BaseModel):
    STATUS_ABERTA = "ABERTA"
    STATUS_PAGA = "PAGA"
    STATUS_CANCELADA = "CANCELADA"
    STATUS_CHOICES = [
        (STATUS_ABERTA, "Aberta"),
        (STATUS_PAGA, "Paga"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="contas_pagar",
    )
    fornecedor = models.ForeignKey(
        "estoque.Fornecedor",
        on_delete=models.PROTECT,
        related_name="contas_pagar",
        null=True,
        blank=True,
    )
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name="contas_pagar",
    )
    valor_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(ONE_CENT)],
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
    data_emissao = models.DateField(default=timezone.localdate)
    data_vencimento = models.DateField()
    data_pagamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTA)
    observacao = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="contas_pagar_criadas",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="contas_pagar_canceladas",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Conta a Pagar"
        verbose_name_plural = "Contas a Pagar"
        constraints = [
            models.CheckConstraint(
                condition=Q(valor_total__gt=0),
                name="financeiro_conta_pagar_total_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_pago__gte=0),
                name="financeiro_conta_pagar_pago_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(valor_restante__gte=0),
                name="financeiro_conta_pagar_restante_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status", "data_vencimento"]),
            models.Index(fields=["company", "fornecedor", "data_vencimento"]),
            models.Index(fields=["company", "categoria", "data_vencimento"]),
            models.Index(fields=["company", "created_by", "created_at"]),
        ]

    def clean(self):
        super().clean()
        self.descricao = (self.descricao or "").strip()
        self.observacao = (self.observacao or "").strip()
        self.motivo_cancelamento = (self.motivo_cancelamento or "").strip()
        self.valor_total = money(self.valor_total)
        self.valor_pago = money(self.valor_pago)
        self.valor_restante = money(self.valor_restante)
        if self.valor_total <= ZERO_MONEY:
            raise ValidationError({"valor_total": "Valor total deve ser maior que zero."})
        if self.valor_restante != money(self.valor_total - self.valor_pago):
            raise ValidationError({
                "valor_restante": "Valor restante deve ser valor_total - valor_pago."
            })
        if self.valor_pago > self.valor_total:
            raise ValidationError({"valor_pago": "Valor pago não pode exceder o total."})
        if self.categoria_id and self.categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
            raise ValidationError({"categoria": "Conta a pagar exige categoria de despesa."})
        if self.fornecedor_id and self.company_id and self.fornecedor.company_id != self.company_id:
            raise ValidationError({"fornecedor": "Fornecedor não pertence à empresa."})
        if self.categoria_id and self.company_id and self.categoria.company_id != self.company_id:
            raise ValidationError({"categoria": "Categoria não pertence à empresa."})

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
            and self.data_vencimento < timezone.localdate()
            and self.valor_restante > ZERO_MONEY
        )

    @property
    def dias_atraso(self) -> int:
        if not self.is_atrasada:
            return 0
        return (timezone.localdate() - self.data_vencimento).days

    def delete(self, *args, **kwargs):
        raise RuntimeError("Conta a pagar não pode ser removida fisicamente.")

    def __str__(self):
        return f"{self.descricao} - {self.status} ({self.valor_restante})"


class CaixaDiario(BaseModel):
    STATUS_ABERTO = "ABERTO"
    STATUS_FECHADO = "FECHADO"
    STATUS_CHOICES = [
        (STATUS_ABERTO, "Aberto"),
        (STATUS_FECHADO, "Fechado"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="caixas_diarios",
    )
    conta_financeira = models.ForeignKey(
        ContaFinanceira,
        on_delete=models.PROTECT,
        related_name="caixas_diarios",
    )
    data = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTO)
    saldo_inicial = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    total_entradas = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    total_saidas = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    saldo_final = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    aberto_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="caixas_abertos",
        null=True,
        blank=True,
    )
    fechado_por = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="caixas_fechados",
        null=True,
        blank=True,
    )
    aberto_em = models.DateTimeField(default=timezone.now)
    fechado_em = models.DateTimeField(null=True, blank=True)
    observacao = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Caixa Diário"
        verbose_name_plural = "Caixas Diários"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "data"],
                condition=Q(deleted_at__isnull=True) & Q(status="ABERTO"),
                name="financeiro_unique_caixa_aberto_company_data",
            ),
            models.CheckConstraint(
                condition=Q(saldo_inicial__gte=0),
                name="financeiro_caixa_saldo_inicial_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(total_entradas__gte=0),
                name="financeiro_caixa_total_entradas_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(total_saidas__gte=0),
                name="financeiro_caixa_total_saidas_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(saldo_final__gte=0),
                name="financeiro_caixa_saldo_final_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "data"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "conta_financeira", "data"]),
        ]

    def clean(self):
        super().clean()
        self.observacao = (self.observacao or "").strip()
        self.saldo_inicial = money(self.saldo_inicial)
        self.total_entradas = money(self.total_entradas)
        self.total_saidas = money(self.total_saidas)
        self.saldo_final = money(self.saldo_final)
        if self.conta_financeira_id:
            if self.conta_financeira.tipo != ContaFinanceira.TIPO_CAIXA:
                raise ValidationError({"conta_financeira": "Caixa diário exige conta tipo CAIXA."})
            if self.company_id and self.conta_financeira.company_id != self.company_id:
                raise ValidationError({"conta_financeira": "Conta não pertence à empresa."})

    def delete(self, *args, **kwargs):
        raise RuntimeError("Caixa diário não pode ser removido fisicamente.")

    def __str__(self):
        return f"Caixa {self.data} - {self.status}"
