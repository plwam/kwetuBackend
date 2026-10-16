from django.db import models


class StatutCourse(models.TextChoices):
    CREEE = "creee", "Créée"
    ACCEPTEE = "acceptee", "Acceptée"
    RECUPEREE = "recuperee", "Récupérée"
    LIVREE = "livree", "Livrée"
    ANNULEE = "annulee", "Annulée"


class StatutAffectation(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    ACCEPTEE = "acceptee", "Acceptée"
    REFUSEE = "refusee", "Refusée"
    EXPIREE = "expiree", "Expirée"