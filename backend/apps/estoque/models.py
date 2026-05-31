from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.empresas.validators import clean_cnpj, is_valid_cnpj


ZERO_MONEY = Decimal("0.00")
ZERO_QTY = Decimal("0.000")


class UnidadeMedida(BaseModel):
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="unidades_medida",
    )
    nome = models.CharField(max_length=120)
    sigla = models.CharField(max_length=20)
    descricao = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Unidade de Medida"
        verbose_name_plural = "Unidades de Medida"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "sigla"],
                condition=Q(deleted_at__isnull=True),
                name="estoque_unique_unidade_sigla_company_active",
            )
        ]
        indexes = [
            models.Index(fields=["company", "sigla"]),
            models.Index(fields=["company", "nome"]),
        ]

    def clean(self):
        super().clean()
        self.sigla = (self.sigla or "").strip().upper()
        self.nome = (self.nome or "").strip()

    def __str__(self):
        return f"{self.nome} ({self.sigla})"


class CategoriaProduto(BaseModel):
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="categorias_produto",
    )
    nome = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Categoria de Produto"
        verbose_name_plural = "Categorias de Produto"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "nome"],
                condition=Q(deleted_at__isnull=True),
                name="estoque_unique_categoria_nome_company_active",
            )
        ]
        indexes = [
            models.Index(fields=["company", "nome"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()

    def __str__(self):
        return self.nome


class Fornecedor(BaseModel):
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="fornecedores",
    )
    razao_social = models.CharField(max_length=300)
    nome_fantasia = models.CharField(max_length=300, blank=True)
    cnpj = models.CharField(max_length=14)
    telefone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    observacoes = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "cnpj"],
                condition=Q(deleted_at__isnull=True),
                name="estoque_unique_fornecedor_cnpj_company_active",
            )
        ]
        indexes = [
            models.Index(fields=["company", "razao_social"]),
            models.Index(fields=["company", "cnpj"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def clean(self):
        super().clean()
        self.razao_social = (self.razao_social or "").strip()
        self.nome_fantasia = (self.nome_fantasia or "").strip()
        self.cnpj = clean_cnpj(self.cnpj or "")
        if not is_valid_cnpj(self.cnpj):
            raise ValidationError({"cnpj": "CNPJ inválido."})

    def __str__(self):
        return self.nome_fantasia or self.razao_social


class Produto(BaseModel):
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="produtos",
    )
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    sku = models.CharField(max_length=80, blank=True)
    codigo_barras = models.CharField(max_length=80, blank=True)
    categoria = models.ForeignKey(
        CategoriaProduto,
        on_delete=models.PROTECT,
        related_name="produtos",
    )
    fornecedor_principal = models.ForeignKey(
        Fornecedor,
        on_delete=models.PROTECT,
        related_name="produtos",
        null=True,
        blank=True,
    )
    unidade = models.ForeignKey(
        UnidadeMedida,
        on_delete=models.PROTECT,
        related_name="produtos",
    )
    preco_compra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    preco_venda = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    custo_medio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    estoque_atual = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=ZERO_QTY,
        validators=[MinValueValidator(ZERO_QTY)],
    )
    estoque_minimo = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=ZERO_QTY,
        validators=[MinValueValidator(ZERO_QTY)],
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "sku"],
                condition=Q(deleted_at__isnull=True) & ~Q(sku=""),
                name="estoque_unique_produto_sku_company_active",
            ),
            models.UniqueConstraint(
                fields=["company", "codigo_barras"],
                condition=Q(deleted_at__isnull=True) & ~Q(codigo_barras=""),
                name="estoque_unique_produto_barcode_company_active",
            ),
            models.CheckConstraint(
                condition=Q(estoque_atual__gte=0),
                name="estoque_produto_estoque_atual_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(estoque_minimo__gte=0),
                name="estoque_produto_estoque_minimo_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(preco_compra__gte=0),
                name="estoque_produto_preco_compra_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(preco_venda__gte=0),
                name="estoque_produto_preco_venda_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(custo_medio__gte=0),
                name="estoque_produto_custo_medio_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "nome"]),
            models.Index(fields=["company", "categoria"]),
            models.Index(fields=["company", "fornecedor_principal"]),
            models.Index(fields=["company", "unidade"]),
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "estoque_atual"]),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        self.sku = (self.sku or "").strip().upper()
        self.codigo_barras = (self.codigo_barras or "").strip()

    def __str__(self):
        return self.nome

    @property
    def estoque_baixo(self) -> bool:
        return self.estoque_atual <= self.estoque_minimo

    @property
    def margem_percentual(self) -> Decimal:
        if self.preco_compra <= ZERO_MONEY:
            return ZERO_MONEY
        margem = ((self.preco_venda - self.preco_compra) / self.preco_compra) * Decimal("100")
        return margem.quantize(Decimal("0.01"))


class MovimentacaoEstoqueQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Movimentação de estoque é imutável e não pode ser editada.")

    def delete(self):
        raise RuntimeError("Movimentação de estoque é imutável e não pode ser removida.")


class MovimentacaoEstoqueManager(models.Manager):
    def get_queryset(self):
        return MovimentacaoEstoqueQuerySet(self.model, using=self._db)


class MovimentacaoEstoque(BaseModel):
    TIPO_ENTRADA = "ENTRADA"
    TIPO_SAIDA = "SAIDA"
    TIPO_AJUSTE = "AJUSTE"
    TIPO_DEVOLUCAO = "DEVOLUCAO"
    TIPO_CANCELAMENTO = "CANCELAMENTO"
    TIPO_CHOICES = [
        (TIPO_ENTRADA, "Entrada"),
        (TIPO_SAIDA, "Saída"),
        (TIPO_AJUSTE, "Ajuste"),
        (TIPO_DEVOLUCAO, "Devolução"),
        (TIPO_CANCELAMENTO, "Cancelamento"),
    ]

    STATUS_ATIVA = "ATIVA"
    STATUS_CANCELADA = "CANCELADA"
    STATUS_CHOICES = [
        (STATUS_ATIVA, "Ativa"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    objects = MovimentacaoEstoqueManager()

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    quantidade_delta = models.DecimalField(max_digits=14, decimal_places=3)
    estoque_antes = models.DecimalField(max_digits=14, decimal_places=3)
    estoque_depois = models.DecimalField(max_digits=14, decimal_places=3)
    custo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    valor_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
        null=True,
        blank=True,
    )
    motivo = models.CharField(max_length=255, blank=True)
    observacao = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ATIVA)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="movimentacoes_estoque",
        null=True,
        blank=True,
    )
    movimentacao_cancelada = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="cancelamentos",
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "idempotency_key"],
                condition=Q(deleted_at__isnull=True) & ~Q(idempotency_key=""),
                name="estoque_unique_mov_key_company_active",
            ),
            models.CheckConstraint(
                condition=~Q(quantidade_delta=0),
                name="estoque_mov_quantidade_delta_not_zero",
            ),
            models.CheckConstraint(
                condition=Q(estoque_antes__gte=0),
                name="estoque_mov_estoque_antes_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(estoque_depois__gte=0),
                name="estoque_mov_estoque_depois_gte_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "produto", "created_at"]),
            models.Index(fields=["company", "tipo", "created_at"]),
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["company", "fornecedor", "created_at"]),
            models.Index(fields=["company", "created_by", "created_at"]),
            models.Index(fields=["company", "idempotency_key"]),
        ]

    def clean(self):
        super().clean()
        self.motivo = (self.motivo or "").strip()
        self.idempotency_key = (self.idempotency_key or "").strip()
        if self.quantidade_delta == ZERO_QTY:
            raise ValidationError({"quantidade_delta": "Quantidade da movimentação não pode ser zero."})
        if self.tipo in {self.TIPO_AJUSTE, self.TIPO_CANCELAMENTO} and not self.motivo:
            raise ValidationError({"motivo": "Motivo é obrigatório para este tipo de movimentação."})

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_allow_status_update", False):
            raise RuntimeError("Movimentação de estoque é imutável e não pode ser editada.")
        super().save(*args, **kwargs)

    def marcar_cancelada(self):
        self.status = self.STATUS_CANCELADA
        self._allow_status_update = True
        try:
            self.save(update_fields=["status", "updated_at"])
        finally:
            self._allow_status_update = False

    def soft_delete(self):
        raise RuntimeError("Movimentação de estoque é imutável e não pode ser removida.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Movimentação de estoque é imutável e não pode ser removida.")

    def __str__(self):
        return f"{self.tipo} {self.produto} ({self.quantidade_delta})"
