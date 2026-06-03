from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {"list", "retrieve"}
DASHBOARD_ACTIONS = {"list"}
MANAGER_ACTIONS = {
    "create",
    "partial_update",
    "ajustar_saldo",
    "cancelar",
    "pagar",
    "abrir",
    "fechar",
    "atualizar",
}
ADMIN_ACTIONS = {"inativar", "reabrir"}


class FinanceiroPermission(BasePermission):
    """
    Role matrix:
        viewer  -> read-only + dashboard
        seller  -> read-only; recebimentos acontecem via Fiado
        manager -> lançamentos, contas a pagar, abrir/fechar caixa
        admin   -> tudo, incluindo reabrir caixa e inativar cadastros
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        require_company(request.user)

        action = getattr(view, "action", None)
        role = getattr(request.user, "role", "")
        basename = getattr(view, "basename", "")

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        if action == "destroy":
            return False
        if basename == "financeiro-dashboard" and action in DASHBOARD_ACTIONS:
            return True
        if action in ADMIN_ACTIONS:
            return role == "admin"
        if action in MANAGER_ACTIONS:
            return role in ("manager", "admin")
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "company_id") and obj.company_id != getattr(request.user, "company_id", None):
            return False
        return self.has_permission(request, view)
