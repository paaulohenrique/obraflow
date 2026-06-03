from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import BaseModel


ZERO_MONEY = Decimal("0.00")
ONE_CENT = Decimal("0.01")
ZERO_QTY = Decimal("0.000")
MIN_QTY = Decimal("0.001")


def money(value: Decimal | None) -> Decimal:
    return (value or ZERO_MONEY).quantize(Decimal("0.01"))


class Venda(BaseModel):
    STATUS_CONCLUIDA = "CONCLUIDA"
    STATUS_CANCELADA = "CANCELADA"
    STATUS_CHOICES = [
        (STATUS_CONCLUIDA, "Concluída"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    FORMA_DINHEIRO = "DINHEIRO"
    FORMA_PIX = "PIX"
    FORMA_CARTAO = "CARTAO"
    FORMA_TRANSFERENCIA = "TRANSFERENCIA"
    FORMA_CHOICES = [
        (FORMA_DINHEIRO, "Dinheiro"),
        (FORMA_PIX, "PIX"),
        (FORMA_CARTAO, "Cartão"),
        (FORMA_TRANSFERENCIA, "Transferência"),
    ]

    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="vendas",
    )
    numero = models.CharField(max_length=20, blank=True)
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="vendas",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONCLUIDA)
    valor_subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    desconto = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    valor_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_CHOICES)
    conta_financeira = models.ForeignKey(
        "financeiro.ContaFinanceira",
        on_delete=models.PROTECT,
        related_name="vendas",
    )
    lancamento_financeiro = models.OneToOneField(
        "financeiro.LancamentoFinanceiro",
        on_delete=models.PROTECT,
        related_name="venda",
        null=True,
        blank=True,
    )
    observacao = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="vendas_criadas",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="vendas_canceladas",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["company", "numero"]),
            models.Index(fields=["company", "cliente", "created_at"]),
            models.Index(fields=["company", "created_at"]),
        ]

    def clean(self):
        super().clean()
        self.numero = (self.numero or "").strip()
        self.observacao = (self.observacao or "").strip()
        self.motivo_cancelamento = (self.motivo_cancelamento or "").strip()
        self.valor_subtotal = money(self.valor_subtotal)
        self.desconto = money(self.desconto)
        self.valor_total = money(self.valor_total)
        if self.desconto < ZERO_MONEY:
            raise ValidationError({"desconto": "Desconto não pode ser negativo."})
        if self.desconto > self.valor_subtotal:
            raise ValidationError({"desconto": "Desconto não pode exceder o subtotal."})
        if self.cliente_id and self.company_id and self.cliente.company_id != self.company_id:
            raise ValidationError({"cliente": "Cliente não pertence à empresa."})
        if self.conta_financeira_id and self.company_id and self.conta_financeira.company_id != self.company_id:
            raise ValidationError({"conta_financeira": "Conta não pertence à empresa."})

    def __str__(self):
        return f"Venda {self.numero} — {self.status}"


class ItemVenda(BaseModel):
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="itens_venda",
    )
    venda = models.ForeignKey(
        Venda,
        on_delete=models.PROTECT,
        related_name="itens",
    )
    produto = models.ForeignKey(
        "estoque.Produto",
        on_delete=models.PROTECT,
        related_name="itens_venda",
    )
    forma_venda = models.ForeignKey(
        "estoque.FormaVendaProduto",
        on_delete=models.PROTECT,
        related_name="itens_venda",
        null=True,
        blank=True,
    )
    # Quantidade informada pelo operador (ex: 2 rolos)
    quantidade_informada = models.DecimalField(
        max_digits=15, decimal_places=3,
        validators=[MinValueValidator(MIN_QTY)],
    )
    # Quantidade em unidade base, após conversão (ex: 200m)
    quantidade = models.DecimalField(
        max_digits=15, decimal_places=3,
        validators=[MinValueValidator(MIN_QTY)],
    )
    preco_unitario = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    movimentacao_estoque = models.OneToOneField(
        "estoque.MovimentacaoEstoque",
        on_delete=models.PROTECT,
        related_name="item_venda",
        null=True,
        blank=True,
    )
    # Snapshot do custo médio no momento da venda — nunca usar produto.custo_medio para relatórios
    custo_unitario_historico = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )
    custo_total_historico = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=ZERO_MONEY,
        validators=[MinValueValidator(ZERO_MONEY)],
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Item de Venda"
        verbose_name_plural = "Itens de Venda"
        indexes = [
            models.Index(fields=["company", "venda"]),
            models.Index(fields=["company", "produto"]),
        ]

    def clean(self):
        super().clean()
        self.preco_unitario = money(self.preco_unitario)
        self.subtotal = money(self.subtotal)
        if self.quantidade_informada <= ZERO_QTY:
            raise ValidationError({"quantidade_informada": "Quantidade deve ser maior que zero."})
        if self.quantidade <= ZERO_QTY:
            raise ValidationError({"quantidade": "Quantidade base deve ser maior que zero."})
        if self.venda_id and self.company_id and self.venda.company_id != self.company_id:
            raise ValidationError({"venda": "Venda não pertence à empresa."})
        if self.produto_id and self.company_id and self.produto.company_id != self.company_id:
            raise ValidationError({"produto": "Produto não pertence à empresa."})

    def __str__(self):
        return f"{self.produto} × {self.quantidade_informada}"
