from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Livreur, Partenaire
from apps.courses.enums import StatutCourse
from apps.courses.models import Course
from apps.logistics.models import Zone

CODE_DE_CONFIRMATION = "483920"
_numero_de_course = count(1000)
_numero_utilisateur = count(1)
Utilisateur = get_user_model()

def _creer_utilisateur(nom, role):
    """Crée un utilisateur selon l'API attendue par ``accounts.UserManager``."""
    numero = next(_numero_utilisateur)
    return Utilisateur.objects.create_user(
        email=f"{nom}-{numero}@exemple.test",
        nom=nom,
        prenom="Test",
        telephone=f"+243900{numero:06d}",
        role=role,
    )

def creer_livreur(nom="patrick", actif=True):
    utilisateur = _creer_utilisateur(nom, "LIVREUR")
    return Livreur.objects.create(user=utilisateur, actif=actif)

def creer_partenaire(nom="kivu_shop"):
    """Renvoie le partenaire « Kivu Shop » (créé au premier appel)."""
    partenaire = Partenaire.objects.filter(nom_boutique="Kivu Shop").first()
    if partenaire is not None:
        return partenaire
    utilisateur = _creer_utilisateur(nom, "PARTENAIRE")
    return Partenaire.objects.create(user=utilisateur, nom_boutique="Kivu Shop")

def creer_administrateur(nom="admin1"):
    return _creer_utilisateur(nom, "ADMIN")

def creer_zone(nom):
    zone, _ = Zone.objects.get_or_create(nom=nom)
    return zone

def creer_course(partenaire=None, **champs):
    """Crée une course (statut « creee » par défaut) avec des valeurs réalistes."""
    numero = next(_numero_de_course)
    valeurs = {
        "reference": f"GM-{numero}",
        "partenaire": partenaire or creer_partenaire(f"boutique{numero}"),
        "zone_depart": creer_zone("Himbi"),
        "zone_arrivee": creer_zone("Birere"),"destinataire_nom": "Amani K.",
        "destinataire_tel": "+243970000099",
        "description_colis": "Sac de vêtements",
        "prix_usd": Decimal("4.00"),
        "statut": StatutCourse.CREEE,
        "code_confirmation": CODE_DE_CONFIRMATION,
    }
    valeurs.update(champs)
    return Course.objects.create(**valeurs)

def client_authentifie(utilisateur):
    """Client d'API qui envoie un vrai jeton JWT (Authorization: Bearer ...)."""
    jeton = RefreshToken.for_user(utilisateur).access_token
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
    return client