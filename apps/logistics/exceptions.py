class LogisticsError(Exception):
    """Exception de base pour le module logistics."""
    code = "logistics_error"
    default_detail = "Une erreur est survenue dans le module logistics."

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class TarifIntrouvable(LogisticsError):
    """Levée quand aucun tarif actif n'existe pour un couple de zones."""
    code = "tarif_introuvable"
    default_detail = "Aucun tarif actif trouvé pour ce trajet."


class ZoneUtilisee(LogisticsError):
    """Levée quand on tente de supprimer une zone référencée par une course."""
    code = "zone_utilisee"
    default_detail = "Cette zone est utilisée par des courses et ne peut pas être supprimée."