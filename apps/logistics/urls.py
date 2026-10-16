from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.logistics.views import DevisView, TarifViewSet, ZoneViewSet

# Router pour les ViewSets (CRUD)
router = DefaultRouter()
router.register(r"zones", ZoneViewSet, basename="zone")
router.register(r"tarifs", TarifViewSet, basename="tarif")

# URLs de l'app
urlpatterns = [
    # Routes admin (générées par le router)
    path("admin/", include(router.urls)),
    # Route partenaire (devis)
    path("partenaire/devis/", DevisView.as_view(), name="devis"),
]