from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .exceptions import EmailDejaUtilise
from .models import CleAPI, DocumentLivreur, DocumentRequis, Livreur, Partenaire, User
from .validators import valider_fichier_document


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
            "mot_de_passe_temporaire",
            "nom_complet",
            "date_creation",
            "partenaire",
            "livreur",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_partenaire(self, obj):
        if hasattr(obj, "partenaire") and obj.partenaire:
            return PartenaireSerializer(obj.partenaire).data
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
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

    def get_cle_api(self, obj) -> str | None:
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
            "verifie",
            "date_creation",
        )
        read_only_fields = ("id", "date_creation", "verifie")

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
        fields = ("disponible", "actif", "verifie")
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


class ChangerMotDePasseSerializer(serializers.Serializer):
    """Aucun champ user_id accepté : on change SEULEMENT le mot de passe de request.user."""

    ancien_mot_de_passe = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    nouveau_mot_de_passe = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirmation = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_ancien_mot_de_passe(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("L'ancien mot de passe est incorrect.")
        return value

    def validate(self, attrs):
        from django.contrib.auth.password_validation import validate_password

        if attrs["nouveau_mot_de_passe"] != attrs["confirmation"]:
            raise serializers.ValidationError(
                {
                    "confirmation": "La confirmation ne correspond pas au nouveau mot de passe."
                }
            )
        if attrs["ancien_mot_de_passe"] == attrs["nouveau_mot_de_passe"]:
            raise serializers.ValidationError(
                {
                    "nouveau_mot_de_passe": "Le nouveau mot de passe doit être différent de l'ancien."
                }
            )
        user = self.context["request"].user
        try:
            validate_password(attrs["nouveau_mot_de_passe"], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                {"nouveau_mot_de_passe": list(e.messages)}
            )
        return attrs

    def save(self, **kwargs):
        from .services import changer_mot_de_passe

        changer_mot_de_passe(
            self.context["request"].user,
            self.validated_data["ancien_mot_de_passe"],
            self.validated_data["nouveau_mot_de_passe"],
        )


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


class LivreurSignupSerializer(serializers.Serializer):
    """Inscription autonome d'un livreur.

    Champs : ``email``, ``password``, ``confirmation``. Le nom, le prénom et le
    téléphone seront complétés ensuite via l'endpoint de profil.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirmation = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise EmailDejaUtilise()
        return value

    def validate(self, attrs):
        from django.contrib.auth.password_validation import validate_password

        if attrs["password"] != attrs["confirmation"]:
            raise serializers.ValidationError(
                {"confirmation": "La confirmation ne correspond pas au mot de passe."}
            )
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        from .services import inscrire_livreur

        return inscrire_livreur(validated_data["email"], validated_data["password"])


class LivreurProfilUpdateSerializer(serializers.Serializer):
    """Attributs du profil qu'un livreur peut compléter lui-même."""

    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    telephone = serializers.CharField(max_length=20)


def resume_documents_livreur(livreur) -> list:
    """Liste, pour un livreur, chaque document requis avec son statut."""
    existants = {d.document_requis_id: d for d in livreur.documents.all()}
    resultat = []
    for requis in DocumentRequis.objects.filter(actif=True):
        document = existants.get(requis.id)
        resultat.append(
            {
                "document_requis": requis.id,
                "nom": requis.nom,
                "description": requis.description,
                "obligatoire": requis.obligatoire,
                "statut": document.statut if document else "manquant",
                "fichier": document.fichier.url if document and document.fichier else None,
                "commentaire": document.commentaire if document else "",
                "date_envoi": document.date_envoi if document else None,
            }
        )
    return resultat


class LivreurProfilSerializer(serializers.ModelSerializer):
    """Vue complète du profil d'un livreur (lecture seule)."""

    nom_complet = serializers.CharField(read_only=True)
    verifie = serializers.BooleanField(source="livreur.verifie", read_only=True)
    disponible = serializers.BooleanField(source="livreur.disponible", read_only=True)
    livreur_actif = serializers.BooleanField(source="livreur.actif", read_only=True)
    profil_complet = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "nom",
            "prenom",
            "telephone",
            "role",
            "nom_complet",
            "verifie",
            "disponible",
            "livreur_actif",
            "profil_complet",
            "documents",
        )
        read_only_fields = fields

    def get_profil_complet(self, obj) -> bool:
        return bool(obj.nom and obj.prenom and obj.telephone)

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_documents(self, obj):
        return resume_documents_livreur(obj.livreur)


class DocumentRequisSerializer(serializers.ModelSerializer):
    """CRUD administrateur des documents exigés aux livreurs."""

    class Meta:
        model = DocumentRequis
        fields = (
            "id",
            "nom",
            "description",
            "obligatoire",
            "actif",
            "ordre",
            "date_creation",
        )
        read_only_fields = ("id", "date_creation")


class DocumentLivreurSerializer(serializers.ModelSerializer):
    """Représentation d'un document envoyé par un livreur (admin)."""

    document_requis_nom = serializers.CharField(
        source="document_requis.nom", read_only=True
    )
    livreur_nom = serializers.CharField(
        source="livreur.user.nom_complet", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = DocumentLivreur
        fields = (
            "id",
            "livreur",
            "livreur_nom",
            "document_requis",
            "document_requis_nom",
            "fichier",
            "statut",
            "statut_display",
            "commentaire",
            "date_envoi",
            "date_validation",
        )
        read_only_fields = (
            "id",
            "livreur",
            "statut",
            "commentaire",
            "date_envoi",
            "date_validation",
        )


class DocumentUploadSerializer(serializers.Serializer):
    """Envoi (ou remplacement) d'un document par un livreur.

    Le fichier doit être un PDF, PNG ou JPEG (le SVG est refusé).
    """

    document_requis = serializers.PrimaryKeyRelatedField(
        queryset=DocumentRequis.objects.filter(actif=True)
    )
    fichier = serializers.FileField()

    def validate_fichier(self, value):
        return valider_fichier_document(value)

    def create(self, validated_data):
        from .services import enregistrer_document

        livreur = self.context["livreur"]
        return enregistrer_document(
            livreur,
            validated_data["document_requis"],
            validated_data["fichier"],
        )


class DocumentStatutSerializer(serializers.Serializer):
    """Commentaire optionnel accompagnant la validation/rejet d'un document."""

    commentaire = serializers.CharField(required=False, allow_blank=True, default="")
