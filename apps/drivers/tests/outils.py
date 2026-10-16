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

def creer_livreur(nom="patrick", actif=True, verifie=True):
    utilisateur = Utilisateur.objects.create_user(
        email=f"{nom}@test.com",
        nom=nom,
        prenom="Livreur",
        telephone="+243970000001",
        password="pass123",
        role="LIVREUR",
    )

    return Livreur.objects.create(user=utilisateur, actif=actif, verifie=verifie)

def creer_partenaire(nom="kivu_shop"):
    utilisateur, _ = Utilisateur.objects.get_or_create(
        email=f"{nom}@test.com",
        defaults={
            "nom": nom,
            "prenom": "Boutique",
            "telephone": "+243970000002",
            "role": "PARTENAIRE",
        },
    )
    partenaire, _ = Partenaire.objects.get_or_create(
        user=utilisateur, defaults={"nom_boutique": "Kivu Shop"}
    )
    return partenaire

def creer_administrateur(nom="admin1"):
    return Utilisateur.objects.create_user(
        email=f"{nom}@test.com",
        nom=nom,
        prenom="Admin",
        telephone="+243970000003",
        password="pass123",
        role="ADMIN",
    )

def creer_zone(nom):
    zone, _ = Zone.objects.get_or_create(nom=nom)
    return zone

def creer_course(partenaire=None, **champs):
    """Crée une course (statut « creee » par défaut) avec des valeurs réalistes."""
    numero = next(_numero_de_course)
    valeurs = {
        "reference": f"GM-{numero}",
        "partenaire": partenaire or creer_partenaire(),
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