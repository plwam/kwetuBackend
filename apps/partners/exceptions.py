from rest_framework import status
from rest_framework.exceptions import APIException


class CourseNonAppartenance(APIException):
    """La course visée n'appartient pas au partenaire authentifié."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Vous n'avez pas la permission d'accéder à cette course."
    default_code = "course_non_appartenance"


class AnnulationImpossible(APIException):
    """La course n'est plus dans un statut annulable (récupérée, livrée, annulée)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Cette course ne peut plus être annulée."
    default_code = "annulation_impossible"


class TarifIntrouvable(APIException):
    """Aucun tarif n'existe pour le couple de zones demandé."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Aucun tarif pour ce couple de zones."
    default_code = "tarif_introuvable"


class WebhookEchec(Exception):
    """Erreur locale lors de l'envoi d'un webhook (non exposée en HTTP)."""

    def __init__(self, message="L'envoi du webhook a échoué."):
        self.message = message
        super().__init__(self.message)
