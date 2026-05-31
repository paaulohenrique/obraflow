from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CategoriaProduto,
    Fornecedor,
    MovimentacaoEstoque,
    Produto,
    UnidadeMedida,
)


@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ("nome", "sigla", "company", "is_active", "created_at")
    list_filter = ("company", "is_active")
    search_fields = ("nome", "sigla", "company__razao_social")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "is_active", "created_at")
    list_filter = ("company", "is_active")
    search_fields = ("nome", "company__razao_social")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("razao_social", "nome_fantasia", "cnpj", "company", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("razao_social", "nome_fantasia", "cnpj", "email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "sku",
        "codigo_barras",
        "categoria",
        "unidade",
        "estoque_atual",
        "estoque_minimo",
        "estoque_baixo_badge",
        "preco_venda",
        "company",
        "is_active",
    )
    list_filter = ("company", "categoria", "unidade", "fornecedor_principal", "is_active")
    search_fields = ("nome", "sku", "codigo_barras", "descricao")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "estoque_baixo_badge")

    @admin.display(description="Estoque baixo")
    def estoque_baixo_badge(self, obj):
        if obj.estoque_baixo:
            return format_html('<span style="color:#b42318;font-weight:600;">Sim</span>')
        return format_html('<span style="color:#027a48;font-weight:600;">Não</span>')


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "tipo",
        "status",
        "produto",
        "quantidade_delta",
        "estoque_antes",
        "estoque_depois",
        "created_by",
        "company",
    )
    list_filter = ("company", "tipo", "status", "produto", "created_by")
    search_fields = ("produto__nome", "produto__sku", "idempotency_key", "motivo", "observacao")
    readonly_fields = (
        "id",
        "company",
        "produto",
        "tipo",
        "quantidade_delta",
        "estoque_antes",
        "estoque_depois",
        "custo_unitario",
        "valor_total",
        "fornecedor",
        "motivo",
        "observacao",
        "status",
        "created_by",
        "movimentacao_cancelada",
        "idempotency_key",
        "metadata",
        "created_at",
        "updated_at",
        "deleted_at",
        "is_active",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
