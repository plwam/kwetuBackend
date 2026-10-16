"""Endpoints d'onboarding du livreur (signup, profil, documents)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import EstLivreurProfil
from .serializers import (
    DocumentLivreurSerializer,
    DocumentUploadSerializer,
    LivreurProfilSerializer,
    LivreurProfilUpdateSerializer,
    LivreurSignupSerializer,
    UserMeSerializer,
    resume_documents_livreur,
)
from .services import completer_profil_livreur


class LivreurSignupView(APIView):
    """Inscription autonome d'un livreur (endpoint **public**).

    N'importe qui peut créer un compte livreur avec un email, un mot de passe et
    sa confirmation. Le compte est créé **non vérifié** : le livreur devra
    compléter son profil puis faire valider les documents exigés par l'admin
    avant de pouvoir accepter des courses. La réponse contient directement les
    jetons JWT pour enchaîner sur la complétion du profil.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=LivreurSignupSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = LivreurSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        livreur = serializer.save()

        refresh = RefreshToken.for_user(livreur.user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserMeSerializer(livreur.user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LivreurProfilView(APIView):
    """Profil du livreur connecté.

    ``GET`` renvoie les informations du compte, l'état de vérification et la
    liste des documents avec leur statut. ``PATCH`` permet de compléter ou de
    mettre à jour le nom, le prénom et le téléphone. Cet endpoint reste
    accessible même si le compte n'est pas encore vérifié.
    """

    permission_classes = [EstLivreurProfil]

    @extend_schema(responses=LivreurProfilSerializer)
    def get(self, request):
        return Response(LivreurProfilSerializer(request.user).data)

    @extend_schema(
        request=LivreurProfilUpdateSerializer,
        responses=LivreurProfilSerializer,
    )
    def patch(self, request):
        serializer = LivreurProfilUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        completer_profil_livreur(request.user, serializer.validated_data)
        return Response(LivreurProfilSerializer(request.user).data)


class LivreurDocumentsView(APIView):
    """Dépôt et suivi des documents de vérification d'un livreur.

    ``GET`` liste les documents exigés par l'administrateur avec, pour chacun,
    le statut du document du livreur (``manquant``, ``en_attente``, ``valide``,
    ``rejete``). ``POST`` envoie ou remplace un document : seuls les formats
    **PDF, PNG et JPEG** sont acceptés (le SVG est refusé). Dès que tous les
    documents obligatoires sont validés par l'admin, le livreur devient vérifié.
    """

    permission_classes = [EstLivreurProfil]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        livreur = request.user.livreur
        return Response(
            {
                "verifie": livreur.verifie,
                "documents": resume_documents_livreur(livreur),
            }
        )

    @extend_schema(
        request=DocumentUploadSerializer,
        responses=DocumentLivreurSerializer,
    )
    def post(self, request):
        serializer = DocumentUploadSerializer(
            data=request.data, context={"livreur": request.user.livreur}
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(
            DocumentLivreurSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )
