from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Autorise uniquement un utilisateur authentifié, actif, avec le rôle ADMIN."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and getattr(user, "role", None) == "ADMIN"
        )