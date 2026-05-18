from .models import AuditLog


def get_audit_logs_for_entity(entity_type: str, entity_id):
    return AuditLog.objects.filter(entity_type=entity_type, entity_id=entity_id).select_related("user")
