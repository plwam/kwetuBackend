from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PartenaireCourseViewSet

router = DefaultRouter()
router.register(r"courses", PartenaireCourseViewSet, basename="partenaire-courses")

urlpatterns = [
    path("", include(router.urls)),
]
