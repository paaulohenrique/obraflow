from django.contrib import admin
from django.utils.html import format_html

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        "nome",
        "tipo_pessoa",
        "cpf_cnpj",
        "telefone",
        "cidade",
        "estado",
        "saldo_devedor",
        "bloqueado_badge",
        "ativo_badge",
        "created_at",
    ]
    list_filter = [
        "tipo_pessoa",
        "bloqueado",
        "is_active",
        "estado",
        "company",
        "created_at",
    ]
    search_fields = ["nome", "cpf_cnpj", "telefone", "whatsapp", "email", "company__razao_social"]
    ordering = ["nome"]
    raw_id_fields = ["company"]
    readonly_fields = [
        "id",
        "saldo_devedor",
        "credito_disponivel_display",
        "deleted_at",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        ("Identificação", {
            "fields": ("id", "company", "nome", "tipo_pessoa", "cpf_cnpj")
        }),
        ("Contato", {
            "fields": ("telefone", "whatsapp", "email")
        }),
        ("Endereço", {
            "fields": ("cep", "rua", "numero", "bairro", "cidade", "estado", "complemento")
        }),
        ("Financeiro", {
            "fields": (
                "limite_credito",
                "saldo_devedor",
                "credito_disponivel_display",
                "bloqueado",
                "data_ultimo_pagamento",
            )
        }),
        ("Observações", {
            "fields": ("observacao",)
        }),
        ("Auditoria", {
            "fields": ("is_active", "deleted_at", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def bloqueado_badge(self, obj):
        if obj.bloqueado:
            return format_html('<span style="color:red;font-weight:bold">🔒 Bloqueado</span>')
        return format_html('<span style="color:green">✓ Ativo</span>')
    bloqueado_badge.short_description = "Status"

    def ativo_badge(self, obj):
        if not obj.is_active:
            return format_html('<span style="color:gray">Removido</span>')
        return format_html('<span style="color:green">✓</span>')
    ativo_badge.short_description = "Ativo"

    def credito_disponivel_display(self, obj):
        return f"R$ {obj.credito_disponivel:,.2f}"
    credito_disponivel_display.short_description = "Crédito Disponível"

    def get_queryset(self, request):
        # Show all records (including soft-deleted) in admin
        return Cliente.objects.all()

    actions = ["bloquear_selecionados", "desbloquear_selecionados"]

    def bloquear_selecionados(self, request, queryset):
        updated = queryset.filter(bloqueado=False).update(bloqueado=True)
        self.message_user(request, f"{updated} cliente(s) bloqueado(s).")
    bloquear_selecionados.short_description = "Bloquear clientes selecionados"

    def desbloquear_selecionados(self, request, queryset):
        updated = queryset.filter(bloqueado=True).update(bloqueado=False)
        self.message_user(request, f"{updated} cliente(s) desbloqueado(s).")
    desbloquear_selecionados.short_description = "Desbloquear clientes selecionados"
