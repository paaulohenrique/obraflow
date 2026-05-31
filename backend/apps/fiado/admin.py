from django.contrib import admin

from .models import ContaFiado, HistoricoFiado, ItemFiado, PagamentoFiado


class _ReadOnlyFiadoAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContaFiado)
class ContaFiadoAdmin(_ReadOnlyFiadoAdmin):
    list_display = (
        "created_at",
        "cliente",
        "status",
        "valor_total",
        "valor_pago",
        "valor_restante",
        "data_vencimento",
        "company",
    )
    list_filter = ("company", "status", "data_vencimento", "created_by")
    search_fields = ("cliente__nome", "cliente__cpf_cnpj", "observacao")
    readonly_fields = (
        "id",
        "company",
        "cliente",
        "status",
        "valor_total",
        "valor_pago",
        "valor_restante",
        "data_abertura",
        "data_vencimento",
        "data_fechamento",
        "observacao",
        "created_by",
        "closed_by",
        "cancelled_by",
        "cancelled_at",
        "motivo_cancelamento",
        "created_at",
        "updated_at",
        "deleted_at",
        "is_active",
    )


@admin.register(ItemFiado)
class ItemFiadoAdmin(_ReadOnlyFiadoAdmin):
    list_display = (
        "created_at",
        "conta",
        "produto",
        "quantidade",
        "preco_unitario",
        "subtotal",
        "status",
        "company",
    )
    list_filter = ("company", "status", "produto", "created_by", "cancelled_by")
    search_fields = ("produto__nome", "produto__sku", "conta__cliente__nome", "idempotency_key")
    readonly_fields = (
        "id",
        "company",
        "conta",
        "produto",
        "quantidade",
        "preco_unitario",
        "subtotal",
        "data_lancamento",
        "movimentacao_estoque",
        "movimentacao_cancelamento",
        "status",
        "created_by",
        "cancelled_by",
        "cancelled_at",
        "motivo_cancelamento",
        "observacao",
        "idempotency_key",
        "created_at",
        "updated_at",
        "deleted_at",
        "is_active",
    )


@admin.register(PagamentoFiado)
class PagamentoFiadoAdmin(_ReadOnlyFiadoAdmin):
    list_display = (
        "data_pagamento",
        "conta",
        "valor",
        "forma_pagamento",
        "status",
        "created_by",
        "company",
    )
    list_filter = ("company", "status", "forma_pagamento", "created_by", "cancelled_by")
    search_fields = ("conta__cliente__nome", "conta__cliente__cpf_cnpj", "idempotency_key")
    readonly_fields = (
        "id",
        "company",
        "conta",
        "valor",
        "forma_pagamento",
        "data_pagamento",
        "status",
        "observacao",
        "created_by",
        "cancelled_by",
        "cancelled_at",
        "motivo_cancelamento",
        "idempotency_key",
        "metadata",
        "created_at",
        "updated_at",
        "deleted_at",
        "is_active",
    )


@admin.register(HistoricoFiado)
class HistoricoFiadoAdmin(_ReadOnlyFiadoAdmin):
    list_display = ("created_at", "evento", "conta", "item", "pagamento", "created_by", "company")
    list_filter = ("company", "evento", "created_by")
    search_fields = ("conta__cliente__nome", "descricao")
    readonly_fields = (
        "id",
        "company",
        "conta",
        "item",
        "pagamento",
        "evento",
        "descricao",
        "before",
        "after",
        "metadata",
        "created_by",
        "created_at",
        "updated_at",
        "deleted_at",
        "is_active",
    )
