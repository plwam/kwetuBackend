from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LivreurViewSet, PartenaireViewSet
from .views_admin_docs import (
    AdminDashboardView,
    DocumentLivreurViewSet,
    DocumentRequisViewSet,
)

router = DefaultRouter()
router.register(r"partenaires", PartenaireViewSet, basename="admin-partenaire")
router.register(r"livreurs", LivreurViewSet, basename="admin-livreur")
router.register(
    r"documents-requis", DocumentRequisViewSet, basename="admin-document-requis"
)
router.register(r"documents", DocumentLivreurViewSet, basename="admin-document")

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    *router.urls,
]
