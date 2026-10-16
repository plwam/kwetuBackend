from rest_framework import permissions


class EstPartenaireOwner(permissions.BasePermission):
    """
    Restriction d'accès aux données (permission locale à ``partners``).

    Vérifie que l'objet manipulé (une course) appartient bien au partenaire
    authentifié. Un partenaire qui vise la course d'un autre reçoit **403**.
    """

    message = "Vous n'avez pas la permission d'accéder à cette course."

    def has_object_permission(self, request, view, obj):
        partenaire = getattr(request.user, "partenaire", None)
        if partenaire is None:
            return False
        return obj.partenaire_id == partenaire.id
