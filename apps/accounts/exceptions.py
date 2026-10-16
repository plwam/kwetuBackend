from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class EmailDejaUtilise(APIException):
    """Email déjà rattaché à un compte existant (renvoyé en HTTP 400)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Cet email est déjà utilisé."
    default_code = "email_deja_utilise"

    def __init__(self, message=None):
        super().__init__(message or self.default_detail)


class CleAPIInvalide(Exception):
    def __init__(self, message="Clé API invalide ou révoquée."):
        self.message = message
        super().__init__(self.message)


class CompteDesactive(Exception):
    def __init__(self, message="Ce compte est désactivé."):
        self.message = message
        super().__init__(self.message)


class PartenaireInactif(Exception):
    def __init__(self, message="Ce partenaire est désactivé."):
        self.message = message
        super().__init__(self.message)


class LivreurInactif(Exception):
    def __init__(self, message="Ce livreur est désactivé."):
        self.message = message
        super().__init__(self.message)


class TransitionInvalide(Exception):
    def __init__(self, message="Transition d'état non autorisée."):
        self.message = message
        super().__init__(self.message)


class AncienMotDePasseInvalide(Exception):
    def __init__(self, message="L'ancien mot de passe est incorrect."):
        self.message = message
        super().__init__(self.message)


class MotDePasseIdentique(Exception):
    def __init__(
        self, message="Le nouveau mot de passe doit être différent de l'ancien."
    ):
        self.message = message
        super().__init__(self.message)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "erreur_inconnue")
        detail = response.data.get("detail", str(exc))

        if isinstance(detail, dict):
            detail = next(iter(detail.values()))
        if isinstance(detail, list):
            detail = detail[0]

        custom_response = {
            "success": False,
            "data": None,
            "error": {"code": error_code, "detail": str(detail)},
        }
        response.data = custom_response

    return response
