from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
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
    ChangerMotDePasseSerializer,
    LivreurSerializer,
    LivreurUpdateSerializer,
    LoginSerializer,
    PartenaireSerializer,
    PartenaireUpdateSerializer,
    UserMeSerializer,
)
from .services import (
    desactiver_livreur,
    desactiver_partenaire,
    generer_cle_api,
    reactiver_livreur,
    reactiver_partenaire,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    """Connexion (admin, partenaire, livreur).

    Authentifie par email et mot de passe et renvoie les jetons JWT
    (``access``, ``refresh``) ainsi que le profil de l'utilisateur. Un compte
    désactivé est refusé.
    """

    serializer_class = LoginSerializer


class RefreshView(TokenRefreshView):
    """Renouvellement du jeton d'accès à partir du jeton de rafraîchissement."""


class MeView(APIView):
    """Profil de l'utilisateur connecté (JWT obligatoire).

    Renvoie l'identité, le rôle et, le cas échéant, le profil partenaire ou
    livreur associé.
    """

    permission_classes: ClassVar[list] = [EstAuthentifie]

    @extend_schema(responses=UserMeSerializer)
    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    """Déconnexion : inscrit le refresh token fourni sur la liste noire.

    Nécessite un JWT valide et le ``refresh`` à invalider.
    """

    permission_classes: ClassVar[list] = [EstAuthentifie]

    @extend_schema(
        request=inline_serializer(
            name="LogoutRequest",
            fields={"refresh": serializers.CharField()},
        ),
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token requis."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Déconnexion réussie."})
        except (TokenError, InvalidToken):
            return Response(
                {"detail": "Token invalide."}, status=status.HTTP_400_BAD_REQUEST
            )


class ChangerMotDePasseView(APIView):
    """POST /auth/changer-mot-de-passe/

    Sécurité :
    - JWT obligatoire : seul le propriétaire du token peut changer SON mot de passe
    - Aucun user_id dans la requête : impossible de cibler un autre compte
    - Ancien mot de passe vérifié (preuve d'identité même si token volé)
    - Tous les refresh tokens invalidés après changement (force re-login partout)
    """

    permission_classes: ClassVar[list] = [EstAuthentifie]

    @extend_schema(
        request=ChangerMotDePasseSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = ChangerMotDePasseSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Mot de passe changé avec succès. " "Veuillez vous reconnecter."
                )
            }
        )


class PartenaireViewSet(viewsets.ModelViewSet):
    """CRUD administrateur des partenaires.

    Permet à l'admin de créer un partenaire (un mot de passe temporaire et une
    première clé API sont générés), de consulter/modifier (nom de boutique, URL
    de webhook, actif) et de régénérer sa clé API.
    """

    permission_classes: ClassVar[list] = [EstAdmin]
    queryset = (
        Partenaire.objects.select_related("user").all().order_by("-date_creation")
    )
    serializer_class = PartenaireSerializer
    ordering = ["-date_creation"]

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return PartenaireUpdateSerializer
        return PartenaireSerializer

    def get_queryset(self):
        return (
            Partenaire.objects.select_related("user").all().order_by("-date_creation")
        )

    @action(detail=True, methods=["post"], url_path="generer-cle")
    def generer_cle(self, request, pk=None):
        partenaire = self.get_object()
        cle_api, cle_complete = generer_cle_api(partenaire)
        serializer = CleAPISerializer(cle_api)
        data = serializer.data
        data["cle_complete"] = cle_complete
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Supprime un partenaire, sauf s'il possède des données rattachées."""
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "Suppression impossible : ce partenaire possède des données "
                        "rattachées (courses). Utilisez la désactivation."
                    ),
                    "code": "suppression_impossible",
                },
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=["post"], url_path="desactiver")
    def desactiver(self, request, pk=None):
        """Désactive un partenaire (et son compte) sans supprimer l'historique."""
        partenaire = desactiver_partenaire(self.get_object().id, request.user)
        return Response(PartenaireSerializer(partenaire).data)

    @action(detail=True, methods=["post"], url_path="reactiver")
    def reactiver(self, request, pk=None):
        """Réactive un partenaire précédemment désactivé."""
        partenaire = reactiver_partenaire(self.get_object().id, request.user)
        return Response(PartenaireSerializer(partenaire).data)


class LivreurViewSet(viewsets.ModelViewSet):
    """CRUD administrateur des livreurs.

    Permet à l'admin de créer, lister, consulter, modifier (disponible, actif,
    vérifié) et supprimer des comptes livreurs. Un livreur créé par l'admin est
    considéré comme vérifié d'emblée.
    """

    permission_classes: ClassVar[list] = [EstAdmin]
    queryset = Livreur.objects.select_related("user").all().order_by("-date_creation")
    serializer_class = LivreurSerializer
    ordering = ["-date_creation"]

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return LivreurUpdateSerializer
        return LivreurSerializer

    def get_queryset(self):
        return Livreur.objects.select_related("user").all().order_by("-date_creation")

    def destroy(self, request, *args, **kwargs):
        """Supprime un livreur, sauf s'il possède des courses rattachées."""
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "Suppression impossible : ce livreur possède des courses "
                        "rattachées. Utilisez la désactivation."
                    ),
                    "code": "suppression_impossible",
                },
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=["post"], url_path="desactiver")
    def desactiver(self, request, pk=None):
        """Désactive un livreur (et son compte) sans perdre l'historique."""
        livreur = desactiver_livreur(self.get_object().id, request.user)
        return Response(LivreurSerializer(livreur).data)

    @action(detail=True, methods=["post"], url_path="reactiver")
    def reactiver(self, request, pk=None):
        """Réactive un livreur précédemment désactivé."""
        livreur = reactiver_livreur(self.get_object().id, request.user)
        return Response(LivreurSerializer(livreur).data)
