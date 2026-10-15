from rest_framework.permissions import BasePermission


class EstAdmin(BasePermission):
    """
    Permission : autorise uniquement les utilisateurs avec le rôle ADMIN.
    """

    message = "Vous devez être administrateur pour accéder à cette ressource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "ADMIN"
        )


class EstPartenaire(BasePermission):
    """
    Permission : autorise uniquement les utilisateurs avec le rôle PARTENAIRE.
    """

    message = "Vous devez être partenaire pour accéder à cette ressource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "PARTENAIRE"
        )