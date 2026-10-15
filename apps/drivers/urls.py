from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.permissions import EstLivreur


class DummyLivreurView(APIView):
    permission_classes = [EstLivreur]
    
    def get(self, request):
        return Response({'detail': 'OK'})


urlpatterns = [
    path('courses/', DummyLivreurView.as_view(), name='livreur-courses'),
]