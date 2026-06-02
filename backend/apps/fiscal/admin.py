from django.contrib import admin

from .models import ConfiguracaoFiscalEmpresa


@admin.register(ConfiguracaoFiscalEmpresa)
class ConfiguracaoFiscalEmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "cnpj",
        "regime_tributario",
        "ambiente_fiscal",
        "provider_fiscal",
        "ativo",
        "cadastro_fiscal_pronto",
    )
    list_filter = ("ambiente_fiscal", "provider_fiscal", "ativo", "regime_tributario")
    search_fields = ("company__razao_social", "cnpj", "razao_social", "nome_fantasia")
    readonly_fields = ("id", "cadastro_fiscal_pronto", "created_at", "updated_at")
