from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company

SAFE_ACTIONS = {"list", "retrieve", "dashboard"}
MANAGER_ACTIONS = {"create", "partial_update", "update", "destroy"}
SELLER_ACTIONS = {
    "enviar_cobranca_fiado",
    "enviar_confirmacao_pagamento",
    "reenviar",
}


class NotificacaoPermission(BasePermission):
    """
    viewer/seller: apenas leitura de notificações;
    seller: pode disparar cobrança para seus clientes;
    manager/admin: fluxo completo.
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
        if action == "reenviar":
            return role in ("seller", "manager", "admin")
        if action in MANAGER_ACTIONS:
            return role in ("manager", "admin")
        return role in ("manager", "admin")

    def has_object_permission(self, request, view, obj):
        if getattr(obj, "company_id", None) != getattr(request.user, "company_id", None):
            return False
        role = getattr(request.user, "role", "")
        if role == "seller" and getattr(obj, "created_by_id", None) != request.user.id:
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                return False
        return self.has_permission(request, view)


class WebhookPermission(BasePermission):
    """Webhook é público — autenticação feita por verify_token ou assinatura."""

    def has_permission(self, request, view):
        return True
