from typing import ClassVar

from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Livreur, Partenaire
from .permissions import EstAdmin, EstAuthentifie
from .serializers import (
    CleAPISerializer,
    LivreurSerializer,
    LivreurUpdateSerializer,
    LoginSerializer,
    PartenaireSerializer,
    PartenaireUpdateSerializer,
    UserMeSerializer,
)
from .services import generer_cle_api

User = get_user_model()


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class RefreshView(TokenRefreshView):
    pass


class MeView(APIView):
    permission_classes: ClassVar[list] = [EstAuthentifie]

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    permission_classes: ClassVar[list] = [EstAuthentifie]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Déconnexion réussie.'})
        except (TokenError, InvalidToken):
            return Response(
                {'detail': 'Token invalide.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PartenaireViewSet(viewsets.ModelViewSet):
    permission_classes: ClassVar[list] = [EstAdmin]
    queryset = Partenaire.objects.select_related('user').all()
    serializer_class = PartenaireSerializer

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return PartenaireUpdateSerializer
        return PartenaireSerializer

    def get_queryset(self):
        return Partenaire.objects.select_related('user').all()

    @action(detail=True, methods=['post'], url_path='generer-cle')
    def generer_cle(self, request, pk=None):
        partenaire = self.get_object()
        cle_api, cle_complete = generer_cle_api(partenaire)
        serializer = CleAPISerializer(cle_api)
        data = serializer.data
        data['cle_complete'] = cle_complete
        return Response(data, status=status.HTTP_201_CREATED)


class LivreurViewSet(viewsets.ModelViewSet):
    permission_classes: ClassVar[list] = [EstAdmin]
    queryset = Livreur.objects.select_related('user').all()
    serializer_class = LivreurSerializer

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return LivreurUpdateSerializer
        return LivreurSerializer

    def get_queryset(self):
        return Livreur.objects.select_related('user').all()