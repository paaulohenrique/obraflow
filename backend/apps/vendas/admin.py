from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = [
        "produto", "forma_venda", "quantidade_informada", "quantidade",
        "preco_unitario", "subtotal", "movimentacao_estoque",
    ]
    can_delete = False


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ["numero", "company", "cliente", "status", "valor_total", "forma_pagamento", "created_at"]
    list_filter = ["status", "forma_pagamento", "company"]
    search_fields = ["numero"]
    readonly_fields = [
        "numero", "company", "cliente", "status", "valor_subtotal", "desconto", "valor_total",
        "forma_pagamento", "conta_financeira", "lancamento_financeiro", "created_by",
        "cancelled_by", "cancelled_at", "motivo_cancelamento", "created_at", "updated_at",
    ]
    inlines = [ItemVendaInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
