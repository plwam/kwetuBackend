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
Utilisateur = get_user_model()

def creer_livreur(nom="patrick", actif=True):
    utilisateur = Utilisateur.objects.create_user(
        username=nom, role="LIVREUR",
        telephone="+243970000001",
    )
    
    return Livreur.objects.create(user=utilisateur, actif=actif)

def creer_partenaire(nom="kivu_shop"):
    utilisateur = Utilisateur.objects.create_user(
        username=nom, role="PARTENAIRE"
    )
    return Partenaire.objects.create(user=utilisateur, nom_boutique="Kivu Shop")

def creer_administrateur(nom="admin1"):
    return Utilisateur.objects.create_user(
        username=nom, role="ADMIN"
    )

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