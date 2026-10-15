from django.contrib import admin

from apps.logistics.models import Tarif, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("nom", "statut", "description")
    list_filter = ("statut",)
    search_fields = ("nom",)


@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    list_display = ("zone_depart", "zone_arrivee", "prix_usd", "actif")
    list_filter = ("actif", "zone_depart", "zone_arrivee")
    search_fields = ("zone_depart__nom", "zone_arrivee__nom")