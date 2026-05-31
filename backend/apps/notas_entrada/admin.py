from django.contrib import admin

from .models import HistoricoNotaFiscalEntrada, ItemNotaFiscalEntrada, NotaFiscalEntrada


@admin.register(NotaFiscalEntrada)
class NotaFiscalEntradaAdmin(admin.ModelAdmin):
    list_display = ["numero", "serie", "data_emissao", "fornecedor_nome_xml", "valor_total", "status", "company"]
    list_filter = ["status", "modelo", "company"]
    search_fields = ["numero", "serie", "chave_acesso", "fornecedor_nome_xml", "fornecedor_cnpj_xml"]
    readonly_fields = ["id", "created_at", "updated_at", "deleted_at", "sha256", "chave_acesso", "payload_extraido"]
    date_hierarchy = "data_emissao"

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ItemNotaFiscalEntrada)
class ItemNotaFiscalEntradaAdmin(admin.ModelAdmin):
    list_display = ["descricao_original", "quantidade", "valor_total_item", "produto", "ignorado", "nota"]
    list_filter = ["ignorado", "company"]
    search_fields = ["descricao_original", "codigo_barras", "codigo_fornecedor"]
    readonly_fields = ["id", "created_at", "updated_at", "nota", "movimentacao_estoque"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoricoNotaFiscalEntrada)
class HistoricoNotaFiscalEntradaAdmin(admin.ModelAdmin):
    list_display = ["evento", "descricao", "nota", "created_by", "created_at"]
    list_filter = ["evento", "company"]
    readonly_fields = ["id", "created_at", "updated_at", "nota", "evento", "descricao", "before", "after", "metadata"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
