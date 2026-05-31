from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {"list", "retrieve", "historico", "dashboard"}
SELLER_ACTIONS = {"create", "itens", "pagamentos"}
MANAGER_ACTIONS = {"partial_update", "cancelar"}


class FiadoPermission(BasePermission):
    """
    Role matrix:
        viewer  -> read-only
        seller  -> read-only + abrir conta/adicionar item/registrar pagamento
        manager -> seller + editar conta + cancelar item/pagamento
        admin   -> all, including cancelar conta
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
        if action == "partial_update":
            return role in ("manager", "admin")
        if action == "cancelar":
            basename = getattr(view, "basename", "")
            if basename == "fiado-conta":
                return role == "admin"
            return role in ("manager", "admin")
        if action in SAFE_ACTIONS:
            return True
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "company_id") and obj.company_id != getattr(request.user, "company_id", None):
            return False
        return self.has_permission(request, view)
