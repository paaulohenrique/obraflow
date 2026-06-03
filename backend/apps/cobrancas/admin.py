from django.contrib import admin

from .models import ConfiguracaoCobranca

@admin.register(ConfiguracaoCobranca)
class ConfiguracaoCobrancaAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "ativo",
        "enviar_1_dia_antes",
        "enviar_no_vencimento",
        "enviar_7_dias_apos",
        "enviar_15_dias_apos",
        "enviar_30_dias_apos",
        "updated_at",
    )
    list_filter = ("ativo", "enviar_no_vencimento", "enviar_7_dias_apos", "enviar_15_dias_apos")
    search_fields = ("company__razao_social", "company__nome_fantasia", "company__cnpj")
    readonly_fields = ("created_at", "updated_at")
