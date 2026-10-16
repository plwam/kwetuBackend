from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PartenaireCourseViewSet, PartenaireDashboardView

router = DefaultRouter()
router.register(r"courses", PartenaireCourseViewSet, basename="partenaire-courses")

urlpatterns = [
    path("dashboard/", PartenaireDashboardView.as_view(), name="partenaire-dashboard"),
    path("", include(router.urls)),
]
