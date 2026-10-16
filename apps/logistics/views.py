from decimal import Decimal

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.accounts.authentication import AuthentificationCleAPI
from apps.logistics.exceptions import TarifIntrouvable, ZoneUtilisee
from apps.logistics.models import StatutZone, Tarif, Zone
from apps.logistics.permissions import EstAdmin, EstPartenaire
from apps.logistics.serializers import (
    DevisRequestSerializer,
    DevisResponseSerializer,
    TarifSerializer,
    ZoneSerializer,
)
from apps.logistics.services import (
    calculer_prix,
    creer_zone,
    modifier_tarif,
    zone_est_utilisee,
)


class ZoneViewSet(ModelViewSet):
    """
    ViewSet pour le CRUD des zones.
    Réservé aux administrateurs.
    """

    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [EstAdmin]

    def create(self, request, *args, **kwargs):
        """
        Crée une nouvelle zone via le service creer_zone().
        Retourne 201 en cas de succès.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            zone = creer_zone(
                nom=serializer.validated_data["nom"],
                description=serializer.validated_data.get("description", ""),
            )
        except IntegrityError:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "zone_existe",
                        "detail": f"Une zone avec le nom '{serializer.validated_data['nom']}' existe déjà.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = self.get_serializer(zone)
        return Response(
            {
                "success": True,
                "data": output_serializer.data,
                "error": None,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Supprime une zone.
        Refuse si la zone est utilisée par une course.
        """
        zone = self.get_object()

        if zone_est_utilisee(zone.id):
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "zone_utilisee",
                        "detail": (
                            f"Impossible de supprimer la zone '{zone.nom}' : "
                            "elle est utilisée par des courses. Désactivez-la à la place."
                        ),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        zone.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TarifViewSet(ModelViewSet):
    """
    ViewSet pour le CRUD des tarifs.
    Réservé aux administrateurs.
    """

    queryset = Tarif.objects.all()
    serializer_class = TarifSerializer
    permission_classes = [EstAdmin]

    def get_queryset(self):
        """
        Optimise les requêtes en chargeant les zones liées.
        Évite le problème N+1.
        """
        return Tarif.objects.select_related(
            "zone_depart",
            "zone_arrivee",
        ).all()

    def update(self, request, *args, **kwargs):
        """
        Modifie un tarif via le service modifier_tarif().
        Gère les modifications partielles (PATCH).
        """
        tarif = self.get_object()
        serializer = self.get_serializer(
            tarif,
            data=request.data,
            partial=kwargs.get("partial", False),
        )
        serializer.is_valid(raise_exception=True)

        tarif = modifier_tarif(
            tarif=tarif,
            prix_usd=serializer.validated_data.get("prix_usd"),
            actif=serializer.validated_data.get("actif"),
        )

        output_serializer = self.get_serializer(tarif)
        return Response(
            {
                "success": True,
                "data": output_serializer.data,
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class DevisView(APIView):
    """
    Vue pour l'endpoint de devis.
    Réservé aux partenaires (authentification par API Key).
    """

    authentication_classes = [AuthentificationCleAPI]
    permission_classes = [EstPartenaire]

    def post(self, request, *args, **kwargs):
        """
        Calcule le prix d'un trajet entre deux zones.
        Retourne le prix en USD.
        """
        serializer = DevisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        zone_depart_id = serializer.validated_data["zone_depart"]
        zone_arrivee_id = serializer.validated_data["zone_arrivee"]

        try:
            prix = calculer_prix(zone_depart_id, zone_arrivee_id)
        except TarifIntrouvable as e:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": e.code,
                        "detail": e.detail,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            zone_depart = Zone.objects.get(id=zone_depart_id)
            zone_arrivee = Zone.objects.get(id=zone_arrivee_id)
        except Zone.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "zone_introuvable",
                        "detail": "Une des zones spécifiées n'existe pas.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "zone_depart": zone_depart.id,
            "zone_depart_nom": zone_depart.nom,
            "zone_arrivee": zone_arrivee.id,
            "zone_arrivee_nom": zone_arrivee.nom,
            "prix_usd": prix,
        }
        output_serializer = DevisResponseSerializer(data)

        return Response(
            {
                "success": True,
                "data": output_serializer.data,
                "error": None,
            },
            status=status.HTTP_200_OK,
        )
    
