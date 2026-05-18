from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "name", "role", "empresa_nome", "is_active", "is_staff", "created_at"]
    list_filter = ["role", "is_active", "is_staff", "company"]
    search_fields = ["email", "name", "company__razao_social"]
    raw_id_fields = ["company"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("name", "role", "company")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "role", "company"),
        }),
    )
    readonly_fields = ["created_at", "updated_at"]

    def empresa_nome(self, obj):
        return obj.company.razao_social if obj.company else "—"
    empresa_nome.short_description = "Empresa"
