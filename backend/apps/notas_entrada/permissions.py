from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company


SAFE_ACTIONS = {"list", "retrieve", "historico", "dashboard", "itens", "item_detalhe"}
MANAGER_ACTIONS = {"upload", "confirmar", "rejeitar", "vincular_fornecedor", "vincular_item", "importar_chave"}


class NotaEntradaPermission(BasePermission):
    """
    admin/manager: acesso completo (upload, revisão, confirmação, rejeição)
    seller/viewer: somente leitura
    anônimo: 401
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        require_company(request.user)
        action = getattr(view, "action", None)
        role = getattr(request.user, "role", "")

        if request.method in ("GET", "HEAD", "OPTIONS") and action in SAFE_ACTIONS:
            return True
        if action in MANAGER_ACTIONS:
            return role in ("manager", "admin")
        if action == "sugestoes_produto":
            return role in ("manager", "admin")
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        company_obj = getattr(obj, "company_id", None) or getattr(getattr(obj, "nota", None), "company_id", None)
        return company_obj == getattr(request.user, "company_id", None)
