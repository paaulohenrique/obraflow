from django.contrib import admin

from .models import BoletoOCR, HistoricoBoleto, OCRProcessamento


@admin.register(BoletoOCR)
class BoletoOCRAdmin(admin.ModelAdmin):
    list_display = (
        "arquivo_nome_original",
        "company",
        "status",
        "fornecedor_nome",
        "banco_nome",
        "valor",
        "vencimento",
        "confianca_ocr",
        "created_at",
    )
    list_filter = ("status", "tipo_arquivo", "company", "created_at", "vencimento")
    search_fields = (
        "arquivo_nome_original",
        "fornecedor_nome",
        "banco_nome",
        "linha_digitavel",
        "codigo_barras",
        "company__razao_social",
    )
    readonly_fields = (
        "sha256",
        "texto_ocr",
        "payload_ocr",
        "raw_provider_response",
        "campos_extraidos",
        "campos_confianca",
        "confianca_ocr",
        "conta_pagar",
        "created_by",
        "processado_por",
        "confirmado_por",
        "rejeitado_por",
        "ocr_started_at",
        "ocr_finished_at",
        "confirmado_at",
        "rejeitado_at",
        "erro_codigo",
        "erro_mensagem",
        "tentativas_ocr",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OCRProcessamento)
class OCRProcessamentoAdmin(admin.ModelAdmin):
    list_display = ("boleto", "company", "provider", "status", "tentativa", "duration_ms", "created_at")
    list_filter = ("provider", "status", "company", "created_at")
    search_fields = ("boleto__arquivo_nome_original", "task_id", "erro_codigo", "erro_mensagem")
    readonly_fields = (
        "company",
        "boleto",
        "provider",
        "status",
        "tentativa",
        "task_id",
        "started_at",
        "finished_at",
        "duration_ms",
        "texto_extraido",
        "payload_response",
        "raw_provider_response",
        "erro_codigo",
        "erro_mensagem",
        "confianca_ocr",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoricoBoleto)
class HistoricoBoletoAdmin(admin.ModelAdmin):
    list_display = ("boleto", "company", "evento", "created_by", "created_at")
    list_filter = ("evento", "company", "created_at")
    search_fields = ("boleto__arquivo_nome_original", "descricao", "request_id")
    readonly_fields = (
        "company",
        "boleto",
        "evento",
        "descricao",
        "before",
        "after",
        "metadata",
        "request_id",
        "created_by",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
