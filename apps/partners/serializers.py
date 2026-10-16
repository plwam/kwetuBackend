from rest_framework import serializers


class PartenaireHistoriqueSerializer(serializers.Serializer):
    """Entrée d'historique d'une course (passage d'un statut à un autre)."""

    ancien_statut = serializers.CharField(read_only=True)
    nouveau_statut = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(source="date_evenement", read_only=True)


class PartenaireCourseDetailSerializer(serializers.Serializer):
    """
    Représentation complète d'une course côté partenaire (lecture seule).

    Le prix est une chaîne décimale, les dates sont en ISO 8601, le statut est
    en minuscules sans accent (``creee``, ``acceptee``, ``recuperee``,
    ``livree``, ``annulee``).
    """

    id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    zone_depart = serializers.SerializerMethodField()
    zone_arrivee = serializers.SerializerMethodField()
    destinataire_nom = serializers.CharField(read_only=True)
    destinataire_tel = serializers.CharField(read_only=True)
    description_colis = serializers.CharField(read_only=True)
    prix = serializers.DecimalField(
        source="prix_usd", max_digits=10, decimal_places=2, read_only=True
    )
    statut = serializers.CharField(read_only=True)
    paye = serializers.BooleanField(read_only=True)
    date_creation = serializers.DateTimeField(read_only=True)
    historique = PartenaireHistoriqueSerializer(many=True, read_only=True)

    def get_zone_depart(self, obj) -> int:
        return getattr(obj, "zone_depart_id", getattr(obj, "zone_depart", None))

    def get_zone_arrivee(self, obj) -> int:
        return getattr(obj, "zone_arrivee_id", getattr(obj, "zone_arrivee", None))


class PartenaireCourseCreateSerializer(serializers.Serializer):
    """
    Entrée de création d'une course.

    Le partenaire ne fournit **que** ces cinq champs : ``prix``, ``statut``,
    ``reference`` et ``paye`` sont calculés ou fixés par le serveur et ignorés
    s'ils sont envoyés.
    """

    zone_depart = serializers.IntegerField()
    zone_arrivee = serializers.IntegerField()
    destinataire_nom = serializers.CharField(max_length=200)
    destinataire_tel = serializers.CharField(max_length=20)
    description_colis = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        from .services import creer_course

        partenaire = self.context["partenaire"]
        return creer_course(partenaire, validated_data)


class PartenaireStatutSerializer(serializers.Serializer):
    """Suivi du statut d'une course (statut courant + historique)."""

    reference = serializers.CharField(read_only=True)
    statut = serializers.CharField(read_only=True)
    historique = PartenaireHistoriqueSerializer(many=True, read_only=True)
