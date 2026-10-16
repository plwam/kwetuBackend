from django.db import models


class WebhookLog(models.Model):
    """
    Trace d'une tentative d'envoi de webhook vers le partenaire.

    Une ligne est créée par **tentative** : une course dont les trois relances
    échouent produit trois lignes. Le champ ``course`` référence la course de
    l'app ``courses`` et est supprimé en cascade avec elle.
    """

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="webhook_logs",
        verbose_name="Course",
    )
    url = models.URLField(verbose_name="URL appelée")
    payload = models.JSONField(verbose_name="Contenu envoyé")
    statut_http = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Statut HTTP",
    )
    succes = models.BooleanField(default=False, verbose_name="Succès")
    date_envoi = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")

    class Meta:
        db_table = "partners_webhook_log"
        verbose_name = "Journal de webhook"
        verbose_name_plural = "Journaux de webhook"
        ordering = ["-date_envoi"]
        indexes = [
            models.Index(fields=["course"]),
        ]

    def __str__(self):
        etat = "OK" if self.succes else "Échec"
        return f"Webhook course #{self.course_id} - {etat} ({self.date_envoi})"
