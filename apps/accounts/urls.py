from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChangerMotDePasseView,
    LivreurViewSet,
    LoginView,
    LogoutView,
    MeView,
    PartenaireViewSet,
    RefreshView,
)

router = DefaultRouter()
router.register(r"partenaires", PartenaireViewSet, basename="admin-partenaire")
router.register(r"livreurs", LivreurViewSet, basename="admin-livreur")

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path(
        "changer-mot-de-passe/",
        ChangerMotDePasseView.as_view(),
        name="auth-changer-mot-de-passe",
    ),
    path("admin/", include(router.urls)),
]

urlpatterns_admin = router.urls
