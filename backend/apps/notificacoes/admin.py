from django.contrib import admin

from .models import (
    CanalNotificacao,
    EventoWebhookWhatsApp,
    Notificacao,
    TemplateNotificacao,
)


@admin.register(CanalNotificacao)
class CanalNotificacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "tipo", "provider", "ativo", "created_at")
    list_filter = ("tipo", "provider", "ativo", "company")
    search_fields = ("nome", "company__razao_social")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
    )

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return [f for f in fields if f != "configuracao"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TemplateNotificacao)
class TemplateNotificacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "tipo", "categoria", "linguagem", "ativo", "created_at")
    list_filter = ("tipo", "categoria", "ativo", "company")
    search_fields = ("nome", "provider_template_name", "company__razao_social")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "tipo",
        "destinatario_nome",
        "destinatario_contato",
        "status",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "tipo", "company", "created_at")
    search_fields = (
        "destinatario_nome",
        "destinatario_contato",
        "provider_message_id",
    )
    readonly_fields = (
        "id",
        "provider_message_id",
        "erro_codigo",
        "erro_mensagem",
        "sent_at",
        "delivered_at",
        "read_at",
        "failed_at",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
    )
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoWebhookWhatsApp)
class EventoWebhookWhatsAppAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "provider_message_id",
        "provider",
        "processed",
        "received_at",
    )
    list_filter = ("event_type", "provider", "processed", "received_at")
    search_fields = ("provider_message_id", "event_type")
    readonly_fields = (
        "id",
        "provider",
        "event_type",
        "provider_message_id",
        "payload",
        "processed",
        "received_at",
    )
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
