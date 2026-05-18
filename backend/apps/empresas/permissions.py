from rest_framework.permissions import BasePermission


class EmpresaPermission(BasePermission):
    """Only platform admins (is_staff/is_superuser) manage companies.

    Regular admin users can only retrieve their own company's data.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        action = getattr(view, "action", None)
        if action in ("list", "retrieve"):
            return request.user.role in ("admin", "manager", "seller", "viewer")
        return request.user.is_staff or request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        action = getattr(view, "action", None)
        if action in ("retrieve",):
            return obj.pk == user.company_id
        return False
