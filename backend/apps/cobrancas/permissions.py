from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {
    "list",
    "retrieve",
    "dashboard",
    "historico_cliente",
    "recuperacao",
}
SELLER_ACTIONS = {
    "preview",
    "enviar",
    "enviar_lote",
}
MANAGER_ACTIONS = {
    "partial_update",
    "update",
    "templates_operacionais",
}


class CobrancaPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        require_company(request.user)
        action = getattr(view, "action", None)
        role = getattr(request.user, "role", "")

        if request.method in ("GET", "HEAD", "OPTIONS") and action in SAFE_ACTIONS:
            return True
        if action in SELLER_ACTIONS:
            return role in ("seller", "manager", "admin")
        if action in MANAGER_ACTIONS:
            return role in ("manager", "admin")
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if getattr(obj, "company_id", None) != getattr(request.user, "company_id", None):
            return False
        return self.has_permission(request, view)
