"""Endpoints administrateur : dashboard et gestion des documents de vérification."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .dashboards import stats_admin
from .models import DocumentLivreur, DocumentRequis
from .permissions import EstAdmin
from .serializers import (
    DocumentLivreurSerializer,
    DocumentRequisSerializer,
    DocumentStatutSerializer,
)
from .services import rejeter_document, valider_document


class AdminDashboardView(APIView):
    """Tableau de bord administrateur.

    Vue d'ensemble de la plateforme : courses par statut, chiffre d'affaires
    livré, partenaires, livreurs (vérifiés / non vérifiés / actifs), zones et
    tarifs, ainsi que le nombre de documents en attente de validation. Tous les
    indicateurs sont calculés côté backend pour alimenter le frontend.
    """

    permission_classes = [EstAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"success": True, "data": stats_admin(), "error": None})


class DocumentRequisViewSet(viewsets.ModelViewSet):
    """CRUD (admin) des documents que les livreurs doivent fournir.

    L'administrateur définit ici la liste des pièces exigées (nom, consignes,
    caractère obligatoire, ordre d'affichage). Ces définitions pilotent l'espace
    documents du livreur : seuls les PDF, PNG et JPEG seront acceptés lors du
    téléversement.
    """

    queryset = DocumentRequis.objects.all()
    serializer_class = DocumentRequisSerializer
    permission_classes = [EstAdmin]


class DocumentLivreurViewSet(viewsets.ReadOnlyModelViewSet):
    """Suivi et validation (admin) des documents envoyés par les livreurs.

    La liste est filtrable via ``?statut=`` et ``?livreur=``. Les actions
    ``valider`` et ``rejeter`` statuent sur un document ; la validation de tous
    les documents obligatoires rend automatiquement le livreur vérifié.
    """

    serializer_class = DocumentLivreurSerializer
    permission_classes = [EstAdmin]

    def get_queryset(self):
        qs = DocumentLivreur.objects.select_related(
            "livreur__user", "document_requis"
        )
        statut = self.request.query_params.get("statut")
        livreur = self.request.query_params.get("livreur")
        if statut:
            qs = qs.filter(statut=statut)
        if livreur:
            qs = qs.filter(livreur_id=livreur)
        return qs

    @extend_schema(
        request=DocumentStatutSerializer,
        responses=DocumentLivreurSerializer,
    )
    @action(detail=True, methods=["post"], url_path="valider")
    def valider(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentStatutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = valider_document(
            document, serializer.validated_data.get("commentaire", "")
        )
        return Response(DocumentLivreurSerializer(document).data)

    @extend_schema(
        request=DocumentStatutSerializer,
        responses=DocumentLivreurSerializer,
    )
    @action(detail=True, methods=["post"], url_path="rejeter")
    def rejeter(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentStatutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = rejeter_document(
            document, serializer.validated_data.get("commentaire", "")
        )
        return Response(DocumentLivreurSerializer(document).data)
