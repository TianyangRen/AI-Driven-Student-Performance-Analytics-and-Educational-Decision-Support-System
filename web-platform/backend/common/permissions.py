from rest_framework.permissions import BasePermission


class IsInstructorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.role in {"INSTRUCTOR", "ADMIN"} or user.is_superuser))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)
