from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class StatutZone(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class Zone(models.Model):
    nom = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nom unique de la zone (ex: Himbi)",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Description optionnelle de la zone",
    )
    statut = models.CharField(
        max_length=10,
        choices=StatutZone.choices,
        default=StatutZone.ACTIVE,
        help_text="Statut de la zone (ACTIVE ou INACTIVE)",
    )

    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Tarif(models.Model):
    zone_depart = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="tarifs_depart",
        help_text="Zone d'origine du trajet",
    )
    zone_arrivee = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="tarifs_arrivee",
        help_text="Zone de destination du trajet",
    )
    prix_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Prix en USD (strictement supérieur à 0)",
    )
    actif = models.BooleanField(
        default=True,
        help_text="Indique si le tarif est utilisable",
    )

    class Meta:
        verbose_name = "Tarif"
        verbose_name_plural = "Tarifs"
        unique_together = [("zone_depart", "zone_arrivee")]
        ordering = ["zone_depart__nom", "zone_arrivee__nom"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(prix_usd__gt=0),
                name="tarif_prix_positif",
            ),
        ]

    def __str__(self):
        return f"{self.zone_depart.nom} → {self.zone_arrivee.nom} : {self.prix_usd} USD"