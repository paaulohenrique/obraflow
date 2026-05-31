from .models import AuditLog


def create_audit_log(*, user, action, entity, before=None, after=None, request=None):
    """Records a mutation event. Call from service layer, not signals."""
    ip = None
    agent = ""
    rid = ""
    if request:
        ip = _get_client_ip(request)
        agent = request.META.get("HTTP_USER_AGENT", "")
        rid = getattr(request, "request_id", "") or ""

    AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=type(entity).__name__,
        entity_id=entity.pk,
        before=before,
        after=after,
        ip_address=ip,
        user_agent=agent,
        request_id=rid,
    )


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
