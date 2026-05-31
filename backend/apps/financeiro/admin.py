from django.contrib import admin

from .models import (
    CaixaDiario,
    CategoriaFinanceira,
    ContaFinanceira,
    ContaPagar,
    LancamentoFinanceiro,
)


@admin.register(ContaFinanceira)
class ContaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "tipo", "saldo_atual", "ativo", "is_active", "created_at")
    list_filter = ("tipo", "ativo", "is_active", "company")
    search_fields = ("nome", "observacao", "company__razao_social")
    readonly_fields = ("saldo_atual", "created_at", "updated_at", "deleted_at")
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "tipo", "ativa", "is_active", "created_at")
    list_filter = ("tipo", "ativa", "is_active", "company")
    search_fields = ("nome", "descricao", "company__razao_social")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = (
        "data_lancamento",
        "company",
        "conta_financeira",
        "categoria",
        "tipo",
        "valor",
        "status",
        "origem_tipo",
        "forma_pagamento",
    )
    list_filter = ("tipo", "status", "origem_tipo", "forma_pagamento", "company")
    search_fields = (
        "descricao",
        "idempotency_key",
        "conta_financeira__nome",
        "categoria__nome",
        "company__razao_social",
    )
    readonly_fields = (
        "company",
        "conta_financeira",
        "categoria",
        "caixa_diario",
        "tipo",
        "valor",
        "data_lancamento",
        "descricao",
        "origem_tipo",
        "origem_id",
        "forma_pagamento",
        "status",
        "created_by",
        "cancelled_by",
        "cancelled_at",
        "motivo_cancelamento",
        "estorno_de",
        "idempotency_key",
        "metadata",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == LancamentoFinanceiro.STATUS_CONFIRMADO:
            return False
        return super().has_change_permission(request, obj)


@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "company",
        "fornecedor",
        "categoria",
        "valor_total",
        "valor_pago",
        "valor_restante",
        "data_vencimento",
        "status",
    )
    list_filter = ("status", "categoria", "company", "data_vencimento")
    search_fields = (
        "descricao",
        "observacao",
        "fornecedor__razao_social",
        "fornecedor__nome_fantasia",
        "company__razao_social",
    )
    readonly_fields = (
        "valor_pago",
        "valor_restante",
        "data_pagamento",
        "created_by",
        "cancelled_by",
        "cancelled_at",
        "motivo_cancelamento",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CaixaDiario)
class CaixaDiarioAdmin(admin.ModelAdmin):
    list_display = (
        "data",
        "company",
        "conta_financeira",
        "status",
        "saldo_inicial",
        "total_entradas",
        "total_saidas",
        "saldo_final",
    )
    list_filter = ("status", "company", "data")
    search_fields = ("conta_financeira__nome", "observacao", "company__razao_social")
    readonly_fields = (
        "saldo_inicial",
        "total_entradas",
        "total_saidas",
        "saldo_final",
        "aberto_por",
        "fechado_por",
        "aberto_em",
        "fechado_em",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False
