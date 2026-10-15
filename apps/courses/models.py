from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.courses.enums import StatutAffectation, StatutCourse


class Course(models.Model):
    reference = models.CharField(max_length=20, unique=True)  # ex : GM-1042

    partenaire = models.ForeignKey(
        "accounts.Partenaire",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    livreur = models.ForeignKey(
        "accounts.Livreur",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="courses",
    )

    zone_depart = models.ForeignKey(
        "logistics.Zone",
        on_delete=models.PROTECT,
        related_name="courses_depart",
    )
    zone_arrivee = models.ForeignKey(
        "logistics.Zone",
        on_delete=models.PROTECT,
        related_name="courses_arrivee",
    )

    destinataire_nom = models.CharField(max_length=150)
    destinataire_tel = models.CharField(max_length=30)
    description_colis = models.TextField()

    prix_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutCourse.choices,
        default=StatutCourse.CREEE,
        db_index=True,
    )
    code_confirmation = models.CharField(max_length=10, blank=True)
    paye = models.BooleanField(default=False)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.reference} ({self.statut})"


class HistoriqueLivraison(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="historique",
    )
    ancien_statut = models.CharField(
        max_length=20,
        choices=StatutCourse.choices,
        blank=True,  # vide pour l'événement de création
    )
    nouveau_statut = models.CharField(
        max_length=20,
        choices=StatutCourse.choices,
    )
    acteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    commentaire = models.TextField(blank=True)
    date_evenement = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date_evenement", "id"]

    def save(self, *args, **kwargs):
        # Append-only : on peut créer une ligne, jamais la modifier.
        if self.pk is not None:
            raise ValueError("L'historique ne peut pas être modifié.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("L'historique ne peut pas être supprimé.")

    def __str__(self):
        return f"{self.course_id}: {self.ancien_statut} -> {self.nouveau_statut}"


class Affectation(models.Model):
    course = models.OneToOneField(
        Course,
        on_delete=models.PROTECT,
        related_name="affectation",
    )
    livreur = models.ForeignKey(
        "accounts.Livreur",
        on_delete=models.PROTECT,
        related_name="affectations",
    )
    date_affectation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20,
        choices=StatutAffectation.choices,
        default=StatutAffectation.EN_ATTENTE,
    )

    def __str__(self):
        return f"{self.course_id} -> {self.livreur_id} ({self.statut})"