from rest_framework.routers import DefaultRouter

from .views import LivreurViewSet, PartenaireViewSet

router = DefaultRouter()
router.register(r'partenaires', PartenaireViewSet, basename='admin-partenaire')
router.register(r'livreurs', LivreurViewSet, basename='admin-livreur')

urlpatterns = router.urls