from django.contrib import admin
from django.utils.html import format_html

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = [
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "plano",
        "limite_usuarios",
        "total_usuarios",
        "ativo_badge",
        "created_at",
    ]
    list_filter = ["plano", "is_active", "created_at"]
    search_fields = ["razao_social", "nome_fantasia", "cnpj", "email"]
    ordering = ["razao_social"]
    readonly_fields = ["id", "created_at", "updated_at", "deleted_at", "total_usuarios"]
    fieldsets = (
        ("Identificação", {"fields": ("id", "razao_social", "nome_fantasia", "cnpj")}),
        ("Contato", {"fields": ("telefone", "email")}),
        ("Plano", {"fields": ("plano", "limite_usuarios", "total_usuarios")}),
        ("Auditoria", {
            "fields": ("is_active", "deleted_at", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def total_usuarios(self, obj):
        return obj.usuarios.filter(is_active=True, deleted_at__isnull=True).count()
    total_usuarios.short_description = "Usuários ativos"

    def ativo_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green">✓ Ativa</span>')
        return format_html('<span style="color:gray">Inativa</span>')
    ativo_badge.short_description = "Status"

    def get_queryset(self, request):
        return Empresa.objects.all()
