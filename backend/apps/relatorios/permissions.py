from rest_framework.permissions import BasePermission

from apps.core.exceptions import require_company


class RelatorioPermission(BasePermission):
    """Read-only reporting access for authenticated users scoped to a company."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        require_company(request.user)
        return request.method in ("GET", "HEAD", "OPTIONS")
