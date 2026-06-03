from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {"list", "retrieve", "dashboard"}
SELLER_ACTIONS = {"create"}
MANAGER_ACTIONS = {"cancelar"}


class VendaPermission(BasePermission):
    """
    Role matrix:
        viewer  -> read-only
        seller  -> pode criar vendas
        manager -> pode cancelar
        admin   -> tudo
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        require_company(request.user)

        action = getattr(view, "action", None)
        role = getattr(request.user, "role", "")

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        if action == "destroy":
            return False
        if action in SELLER_ACTIONS:
            return role in ("seller", "manager", "admin")
        if action in MANAGER_ACTIONS:
            return role in ("manager", "admin")
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "company_id") and obj.company_id != getattr(request.user, "company_id", None):
            return False
        return self.has_permission(request, view)
