from django.contrib import admin

from .models import WebhookLog


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    """
    Consultation des journaux de webhook.

    Réservé à l'administration : les ``WebhookLog`` ne sont jamais exposés à
    l'API partenaire.
    """

    list_display = ("id", "course", "url", "statut_http", "succes", "date_envoi")
    list_filter = ("succes",)
    search_fields = ("course__reference", "url")
    readonly_fields = (
        "course",
        "url",
        "payload",
        "statut_http",
        "succes",
        "date_envoi",
    )
