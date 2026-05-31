from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company


SAFE_ACTIONS = {"list", "retrieve", "historico", "dashboard", "download"}
MANAGER_ACTIONS = {"confirmar", "rejeitar", "reprocessar"}
SELLER_ACTIONS = {"upload"}


class BoletoPermission(BasePermission):
    """
    viewer: leitura/dashboard; seller: upload e leitura dos próprios;
    manager/admin: fluxo completo, sem delete físico na V1.
    """

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
        if action == "destroy":
            return False
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if getattr(obj, "company_id", None) != getattr(request.user, "company_id", None):
            return False
        if getattr(request.user, "role", "") == "seller" and obj.created_by_id != request.user.id:
            return False
        return self.has_permission(request, view)
