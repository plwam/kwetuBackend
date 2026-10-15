from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.accounts.permissions import EstPartenaire


class DummyPartenaireView(APIView):
    permission_classes = [EstPartenaire]
    
    def get(self, request):
        return Response({'detail': 'OK'})


urlpatterns = [
    path('courses/', DummyPartenaireView.as_view(), name='partenaire-courses'),
]