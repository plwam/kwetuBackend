from rest_framework import permissions

from apps.accounts.enums import Role


class EstAdmin(permissions.BasePermission):
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class EstPartenaire(permissions.BasePermission):
    message = "Accès réservé aux partenaires."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.PARTENAIRE
        )