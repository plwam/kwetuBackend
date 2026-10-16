from django.contrib import admin

from apps.logistics.models import Tarif, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des zones dans l'admin Django.
    """

    list_display = ("nom", "statut", "description_courte")
    list_filter = ("statut",)
    search_fields = ("nom", "description")
    ordering = ("nom",)

    def description_courte(self, obj):
        """
        Affiche les 50 premiers caractères de la description.
        """
        if len(obj.description) > 50:
            return obj.description[:50] + "..."
        return obj.description
    description_courte.short_description = "Description"


@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des tarifs dans l'admin Django.
    """

    list_display = (
        "zone_depart",
        "zone_arrivee",
        "prix_usd",
        "actif",
    )
    list_filter = ("actif", "zone_depart", "zone_arrivee")
    search_fields = ("zone_depart__nom", "zone_arrivee__nom")
    list_select_related = ("zone_depart", "zone_arrivee")
    ordering = ("zone_depart__nom", "zone_arrivee__nom")