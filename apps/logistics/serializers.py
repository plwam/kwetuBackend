from decimal import Decimal

from rest_framework import serializers

from apps.logistics.models import Tarif, Zone


class ZoneSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Zone.
    Utilisé pour le CRUD admin.

    La contrainte d'unicité du nom n'est pas validée ici : ``ZoneViewSet.create``
    la gère explicitement pour renvoyer le code ``zone_existe``.
    """

    nom = serializers.CharField(max_length=100)

    class Meta:
        model = Zone
        fields = ["id", "nom", "description", "statut"]
        read_only_fields = ["id"]


class TarifSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Tarif.
    Utilisé pour le CRUD admin.
    Inclut les noms des zones pour l'affichage.
    """

    zone_depart_nom = serializers.CharField(
        source="zone_depart.nom",
        read_only=True,
    )
    zone_arrivee_nom = serializers.CharField(
        source="zone_arrivee.nom",
        read_only=True,
    )

    class Meta:
        model = Tarif
        fields = [
            "id",
            "zone_depart",
            "zone_depart_nom",
            "zone_arrivee",
            "zone_arrivee_nom",
            "prix_usd",
            "actif",
        ]
        read_only_fields = ["id"]

    def validate_prix_usd(self, value):
        """
        Vérifie que le prix est strictement supérieur à 0.
        """
        if value <= Decimal("0"):
            raise serializers.ValidationError(
                "Le prix doit être strictement supérieur à 0."
            )
        return value


class DevisRequestSerializer(serializers.Serializer):
    """
    Serializer pour valider l'entrée d'un devis.
    Reçoit deux IDs de zones.
    """

    zone_depart = serializers.IntegerField(
        min_value=1,
        help_text="ID de la zone de départ",
    )
    zone_arrivee = serializers.IntegerField(
        min_value=1,
        help_text="ID de la zone d'arrivée",
    )


class DevisResponseSerializer(serializers.Serializer):
    """
    Serializer pour formater la sortie d'un devis.
    Inclut les noms des zones et le prix calculé.
    """

    zone_depart = serializers.IntegerField(read_only=True)
    zone_depart_nom = serializers.CharField(read_only=True)
    zone_arrivee = serializers.IntegerField(read_only=True)
    zone_arrivee_nom = serializers.CharField(read_only=True)
    prix_usd = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )