from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """Allow access only to object owners or staff users."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "created_by", None)
        return owner == request.user


class IsSameCompany(BasePermission):
    """Ensures the user can only access resources from their own company."""

    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, "company_id"):
            return True
        return obj.company_id == getattr(request.user, "company_id", None)
