from rest_framework.views import exception_handler


class EmailDejaUtilise(Exception):
    def __init__(self, message="Cet email est déjà utilisé."):
        self.message = message
        super().__init__(self.message)


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
