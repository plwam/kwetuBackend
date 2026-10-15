import hashlib
import secrets
from typing import ClassVar

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .enums import Role, StatutCleAPI


class UserManager(BaseUserManager):
    def create_user(self, email, nom, prenom, telephone, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(
            email=email, nom=nom, prenom=prenom, telephone=telephone, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email, nom, prenom, telephone, password=None, **extra_fields
    ):
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("actif", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(
            email, nom, prenom, telephone, password=password, **extra_fields
        )


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    role = models.CharField(max_length=20, choices=Role.choices(), verbose_name="Rôle")
    actif = models.BooleanField(default=True, verbose_name="Compte actif")
    date_creation = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )
    date_modification = models.DateTimeField(
        auto_now=True, verbose_name="Date de modification"
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["nom", "prenom", "telephone", "role"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def est_admin(self):
        return self.role == Role.ADMIN

    def est_partenaire(self):
        return self.role == Role.PARTENAIRE

    def est_livreur(self):
        return self.role == Role.LIVREUR


class Partenaire(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="partenaire",
        verbose_name="Utilisateur",
    )
    nom_boutique = models.CharField(
        max_length=200, unique=True, verbose_name="Nom de la boutique"
    )
    url_webhook = models.URLField(blank=True, null=True, verbose_name="URL de webhook")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    date_creation = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )
    date_modification = models.DateTimeField(
        auto_now=True, verbose_name="Date de modification"
    )

    class Meta:
        db_table = "accounts_partenaire"
        verbose_name = "Partenaire"
        verbose_name_plural = "Partenaires"

    def __str__(self):
        return self.nom_boutique

    def cle_api_active(self):
        return self.cles_api.filter(statut=StatutCleAPI.ACTIVE).first()

    def generer_cle_api(self):
        from .services import generer_cle_api

        return generer_cle_api(self)


class Livreur(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="livreur",
        verbose_name="Utilisateur",
    )
    disponible = models.BooleanField(default=False, verbose_name="Disponible")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    date_creation = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )
    date_modification = models.DateTimeField(
        auto_now=True, verbose_name="Date de modification"
    )

    class Meta:
        db_table = "accounts_livreur"
        verbose_name = "Livreur"
        verbose_name_plural = "Livreurs"

    def __str__(self):
        return f"{self.user.nom_complet} ({self.user.email})"


class CleAPI(models.Model):
    partenaire = models.ForeignKey(
        Partenaire,
        on_delete=models.CASCADE,
        related_name="cles_api",
        verbose_name="Partenaire",
    )
    prefixe = models.CharField(max_length=20, verbose_name="Préfixe")
    hash_cle = models.CharField(max_length=128, verbose_name="Hash de la clé")
    statut = models.CharField(
        max_length=20,
        choices=StatutCleAPI.choices(),
        default=StatutCleAPI.ACTIVE,
        verbose_name="Statut",
    )
    date_creation = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )
    date_revocation = models.DateTimeField(
        null=True, blank=True, verbose_name="Date de révocation"
    )

    class Meta:
        db_table = "accounts_cle_api"
        verbose_name = "Clé API"
        verbose_name_plural = "Clés API"
        ordering = ("-date_creation",)

    def __str__(self):
        return f"{self.prefixe}... ({self.statut})"

    @staticmethod
    def hasher_cle(cle: str) -> str:
        return hashlib.sha256(cle.encode()).hexdigest()

    @classmethod
    def generer_cle(cls) -> tuple[str, str]:
        secret = secrets.token_urlsafe(32)
        prefixe = f"pk_live_{secrets.token_urlsafe(8)}"
        cle_complete = f"{prefixe}_{secret}"
        return cle_complete, cls.hasher_cle(cle_complete)

    def verifier_cle(self, cle: str) -> bool:
        import hmac

        return hmac.compare_digest(self.hash_cle, self.hasher_cle(cle))

    def revoquer(self):
        self.statut = StatutCleAPI.REVOQUEE
        self.date_revocation = timezone.now()
        self.save(update_fields=["statut", "date_revocation"])
