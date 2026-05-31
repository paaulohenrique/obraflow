from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {"list", "retrieve", "inadimplentes", "bloqueados"}
WRITE_ACTIONS = {"create"}
MANAGER_ACTIONS = {"update", "partial_update", "bloquear", "desbloquear"}
ADMIN_ACTIONS = {"destroy"}


class ClientePermission(BasePermission):
    """
    Role matrix:
        viewer  → safe (read-only)
        seller  → safe + create
        manager → safe + create + update/partial_update + bloquear/desbloquear
        admin   → all actions including destroy
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Every tenant-scoped operation requires a company association.
        require_company(request.user)

        action = getattr(view, "action", None)
        role = getattr(request.user, "role", "")

        if action in SAFE_ACTIONS:
            return True
        if action in WRITE_ACTIONS:
            return role in ("seller", "manager", "admin")
        if action in MANAGER_ACTIONS:
            return role in ("manager", "admin")
        if action in ADMIN_ACTIONS:
            return role == "admin"
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        user = request.user
        action = getattr(view, "action", None)

        # Tenant isolation: company_id on both User and Cliente are FK columns (UUID values)
        if obj.company_id and user.company_id and obj.company_id != user.company_id:
            return False

        if action in SAFE_ACTIONS:
            return True
        if action in WRITE_ACTIONS:
            return user.role in ("seller", "manager", "admin")
        if action in MANAGER_ACTIONS:
            return user.role in ("manager", "admin")
        if action in ADMIN_ACTIONS:
            return user.role == "admin"
        return False
