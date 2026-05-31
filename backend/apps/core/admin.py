from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "user", "ip_address", "request_id", "created_at"]
    list_filter = ["action", "entity_type", "created_at"]
    search_fields = ["entity_id", "user__email", "ip_address", "request_id"]
    readonly_fields = ["id", "user", "action", "entity_type", "entity_id", "before", "after", "ip_address", "user_agent", "request_id", "created_at"]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
