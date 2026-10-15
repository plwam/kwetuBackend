from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .exceptions import EmailDejaUtilise
from .models import CleAPI, Livreur, Partenaire, User


class UserSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "nom",
            "prenom",
            "telephone",
            "role",
            "role_display",
            "actif",
            "nom_complet",
            "date_creation",
        )
        read_only_fields = ("id", "date_creation", "role")


class UserMeSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    partenaire = serializers.SerializerMethodField()
    livreur = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "nom",
            "prenom",
            "telephone",
            "role",
            "role_display",
            "actif",
            "nom_complet",
            "date_creation",
            "partenaire",
            "livreur",
        )
        read_only_fields = fields

    def get_partenaire(self, obj):
        if hasattr(obj, "partenaire") and obj.partenaire:
            return PartenaireSerializer(obj.partenaire).data
        return None

    def get_livreur(self, obj):
        if hasattr(obj, "livreur") and obj.livreur:
            return LivreurSerializer(obj.livreur).data
        return None


class PartenaireSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True)
    nom = serializers.CharField(write_only=True)
    prenom = serializers.CharField(write_only=True)
    telephone = serializers.CharField(write_only=True)
    mot_de_passe = serializers.CharField(write_only=True, required=True)
    cle_api = serializers.SerializerMethodField()

    class Meta:
        model = Partenaire
        fields = (
            "id",
            "user",
            "user_id",
            "email",
            "nom",
            "prenom",
            "telephone",
            "mot_de_passe",
            "nom_boutique",
            "url_webhook",
            "actif",
            "cle_api",
            "date_creation",
        )
        read_only_fields = ("id", "date_creation", "cle_api")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise EmailDejaUtilise()
        return value

    def validate_nom_boutique(self, value):
        if Partenaire.objects.filter(nom_boutique=value, actif=True).exists():
            raise serializers.ValidationError(
                "Ce nom de boutique est déjà utilisé par un partenaire actif."
            )
        return value

    def get_cle_api(self, obj):
        return getattr(obj, "_cle_api_complete", None)

    def create(self, validated_data):
        from .services import creer_partenaire

        return creer_partenaire(validated_data)


class PartenaireUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partenaire
        fields = ("nom_boutique", "url_webhook", "actif")
        read_only_fields = ("id", "date_creation")


class LivreurSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True)
    nom = serializers.CharField(write_only=True)
    prenom = serializers.CharField(write_only=True)
    telephone = serializers.CharField(write_only=True)
    mot_de_passe = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Livreur
        fields = (
            "id",
            "user",
            "user_id",
            "email",
            "nom",
            "prenom",
            "telephone",
            "mot_de_passe",
            "disponible",
            "actif",
            "date_creation",
        )
        read_only_fields = ("id", "date_creation")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise EmailDejaUtilise()
        return value

    def create(self, validated_data):
        from .services import creer_livreur

        return creer_livreur(validated_data)


class LivreurUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livreur
        fields = ("disponible", "actif")
        read_only_fields = ("id", "date_creation")


class CleAPISerializer(serializers.ModelSerializer):
    cle_complete = serializers.CharField(read_only=True)

    class Meta:
        model = CleAPI
        fields = (
            "id",
            "prefixe",
            "cle_complete",
            "statut",
            "date_creation",
            "date_revocation",
        )
        read_only_fields = fields


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if not user.actif:
            raise serializers.ValidationError("Ce compte est désactivé.")
        data["user"] = UserMeSerializer(user).data
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["user_id"] = user.id
        return token
