from rest_framework import serializers

class SerialiseurCourseDisponible(serializers.Serializer):
    """Course proposée au livreur AVANT acceptation (informations minimales)."""
    id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    zone_depart = serializers.CharField(source="zone_depart.nom", read_only=True)
    zone_arrivee = serializers.CharField(source="zone_arrivee.nom", read_only=True)
    destinataire_nom = serializers.CharField(read_only=True)
    description_colis = serializers.CharField(read_only=True)
    prix_usd = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    statut = serializers.CharField(read_only=True)
    date_creation = serializers.DateTimeField(read_only=True)

class SerialiseurCourseEnCours(serializers.Serializer):
    """Course du livreur après acceptation (téléphone et partenaire visibles)."""
    id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    zone_depart = serializers.CharField(source="zone_depart.nom", read_only=True)
    zone_arrivee = serializers.CharField(source="zone_arrivee.nom", read_only=True)
    partenaire_nom = serializers.CharField(
        source="partenaire.nom_boutique", read_only=True
    )
    destinataire_nom = serializers.CharField(read_only=True)
    destinataire_tel = serializers.CharField(read_only=True)
    description_colis = serializers.CharField(read_only=True)
    prix_usd = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    statut = serializers.CharField(read_only=True)
    paye = serializers.BooleanField(read_only=True)
    date_creation = serializers.DateTimeField(read_only=True)
    date_livraison = serializers.DateTimeField(read_only=True, allow_null=True)

class SerialiseurCourseHistorique(serializers.Serializer):
    """Course livrée, affichée dans l'historique du jour."""
    id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    zone_depart = serializers.CharField(source="zone_depart.nom", read_only=True)
    zone_arrivee = serializers.CharField(source="zone_arrivee.nom", read_only=True)
    destinataire_nom = serializers.CharField(read_only=True)
    prix_usd = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    paye = serializers.BooleanField(read_only=True)
    date_livraison = serializers.DateTimeField(read_only=True)
    
class SerialiseurLivraison(serializers.Serializer):
    """Corps de la requête de livraison : le code donné par le destinataire."""
    code = serializers.CharField(
        max_length=64,
        trim_whitespace=True,
        allow_blank=False,
        error_messages={
            "required": "Le code de confirmation est obligatoire.",
            "blank": "Le code de confirmation ne peut pas être vide.",
        },
    )