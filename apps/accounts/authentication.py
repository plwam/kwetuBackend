from rest_framework import authentication, exceptions

from .enums import StatutCleAPI
from .models import CleAPI


class AuthentificationCleAPI(authentication.BaseAuthentication):
    keyword = 'X-API-Key'

    def authenticate(self, request):
        cle = request.headers.get('X-API-Key')
        if not cle:
            return None

        # Format: pk_live_{prefix}_{secret}
        # Prefix stocké en base: pk_live_{prefix}
        parts = cle.split('_')
        if len(parts) < 4 or parts[0] != 'pk' or parts[1] != 'live':
            raise exceptions.AuthenticationFailed('Format de clé API invalide.')
        
        prefixe = '_'.join(parts[:3])  # pk_live_{prefix}

        try:
            cle_api = CleAPI.objects.select_related('partenaire__user').get(
                prefixe=prefixe,
                statut=StatutCleAPI.ACTIVE
            )
        except CleAPI.DoesNotExist:
            raise exceptions.AuthenticationFailed('Clé API invalide ou révoquée.')

        if not cle_api.verifier_cle(cle):
            raise exceptions.AuthenticationFailed('Clé API invalide.')

        if not cle_api.partenaire.actif:
            raise exceptions.AuthenticationFailed('Ce partenaire est désactivé.')

        if not cle_api.partenaire.user.actif:
            raise exceptions.AuthenticationFailed('Le compte utilisateur associé est désactivé.')

        return (cle_api.partenaire.user, cle_api)

    def authenticate_header(self, request):
        return 'ApiKey'