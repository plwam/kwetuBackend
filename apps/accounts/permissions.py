from rest_framework import permissions

from .enums import Role


class EstAuthentifie(permissions.BasePermission):
    message = "Authentification requise."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


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


class EstLivreur(permissions.BasePermission):
    message = "Accès réservé aux livreurs."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.LIVREUR
        )


class EstPartenaireOwner(permissions.BasePermission):
    message = "Vous ne pouvez accéder qu'à vos propres ressources."

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "partenaire"):
            return obj.partenaire.user == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False


class EstLivreurOwner(permissions.BasePermission):
    message = "Vous ne pouvez accéder qu'à vos propres ressources."

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "livreur"):
            return obj.livreur.user == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False
