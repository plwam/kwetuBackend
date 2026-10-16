from rest_framework import serializers

from apps.courses.models import Course, HistoriqueLivraison


class HistoriqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoriqueLivraison
        fields = [
            "id",
            "ancien_statut",
            "nouveau_statut",
            "acteur",
            "commentaire",
            "date_evenement",
        ]
        read_only_fields = fields


class CourseSerializer(serializers.ModelSerializer):
    """Version courte, pour la liste."""

    partenaire_nom = serializers.CharField(source="partenaire.nom_boutique", read_only=True)
    zone_depart_nom = serializers.CharField(source="zone_depart.nom", read_only=True)
    zone_arrivee_nom = serializers.CharField(source="zone_arrivee.nom", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "reference",
            "statut",
            "partenaire",
            "partenaire_nom",
            "livreur",
            "zone_depart",
            "zone_depart_nom",
            "zone_arrivee",
            "zone_arrivee_nom",
            "prix_usd",
            "paye",
            "date_creation",
        ]
        read_only_fields = fields


class CourseDetailSerializer(CourseSerializer):
    """Version complète, avec historique."""

    historique = HistoriqueSerializer(many=True, read_only=True)

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + [
            "destinataire_nom",
            "destinataire_tel",
            "description_colis",
            "date_livraison",
            "historique",
        ]
        read_only_fields = fields


class AssignerSerializer(serializers.Serializer):
    livreur_id = serializers.IntegerField(min_value=1)