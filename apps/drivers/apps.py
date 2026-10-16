from django.apps import AppConfig

class ConfigurationDrivers(AppConfig):
    """Configuration de l'application drivers (espace livreur)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.drivers"
    label = "drivers"
    verbose_name = "Espace livreur"