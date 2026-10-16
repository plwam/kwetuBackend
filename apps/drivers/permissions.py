from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
ROLE_LIVREUR = "LIVREUR"

class EstLivreur(BasePermission):
    def has_permission(self, request, view):
        utilisateur = request.user
        if not utilisateur or not utilisateur.is_authenticated:
            return False
        
        if getattr(utilisateur, "role", None) != ROLE_LIVREUR:
            raise PermissionDenied(
                "Cet espace est réservé aux livreurs.", code="acces_refuse"
            )
        profil_livreur = getattr(utilisateur, "livreur", None)

        if profil_livreur is None:
            raise PermissionDenied(
                "Aucun profil livreur n'est associé à ce compte.",
                code="acces_refuse",
            )
        
        if not profil_livreur.actif:
            raise PermissionDenied(
                "Votre compte livreur est désactivé.", code="compte_desactive"
            )
        
        if not profil_livreur.verifie:
            raise PermissionDenied(
                "Votre compte livreur n'est pas encore vérifié. "
                "Complétez votre profil et faites valider vos documents.",
                code="compte_non_verifie",
            )
        
        return True 