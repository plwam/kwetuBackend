from django.urls import path

from .views_livreur import LivreurDocumentsView, LivreurProfilView

urlpatterns = [
    path("profil/", LivreurProfilView.as_view(), name="livreur-profil"),
    path("documents/", LivreurDocumentsView.as_view(), name="livreur-documents"),
]
