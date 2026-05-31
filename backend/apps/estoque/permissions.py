from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {"list", "retrieve", "baixo_estoque", "movimentacoes"}
MANAGER_CATALOG_ACTIONS = {"create", "update", "partial_update", "ativar", "inativar"}
ADMIN_ACTIONS = {"destroy"}
MANAGER_MOVEMENT_ACTIONS = {"entrada", "ajuste", "devolucao", "cancelar"}
SELLER_MOVEMENT_ACTIONS = {"saida"}


class EstoquePermission(BasePermission):
    """
    Role matrix:
        viewer  -> read-only
        seller  -> read-only + manual stock saída
        manager -> product/catalog write + stock entry/adjust/devolution/cancel
        admin   -> all, including soft-delete of catalog/product records
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        require_company(request.user)

        action = getattr(view, "action", None)
        role = getattr(request.user, "role", "")

        if action in SAFE_ACTIONS:
            return True
        if action in MANAGER_CATALOG_ACTIONS:
            return role in ("manager", "admin")
        if action in ADMIN_ACTIONS:
            return role == "admin"
        if action in MANAGER_MOVEMENT_ACTIONS:
            return role in ("manager", "admin")
        if action in SELLER_MOVEMENT_ACTIONS:
            return role in ("seller", "manager", "admin")
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "company_id") and obj.company_id != getattr(request.user, "company_id", None):
            return False
        return self.has_permission(request, view)
