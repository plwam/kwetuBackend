from decimal import Decimal

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.enums import Role, StatutCleAPI
from apps.accounts.models import CleAPI, Partenaire

User = get_user_model()


def _creer_partenaire(email, nom_boutique, url_webhook=None):
    """Crée un utilisateur PARTENAIRE, son profil et une clé API active."""
    user = User.objects.create_user(
        email=email,
        nom="Kabila",
        prenom="Amani",
        telephone="+243970000000",
        role=Role.PARTENAIRE,
        password="pass123",
    )
    partenaire = Partenaire.objects.create(
        user=user, nom_boutique=nom_boutique, url_webhook=url_webhook
    )
    cle_complete, hash_cle = CleAPI.generer_cle()
    prefixe = "_".join(cle_complete.split("_")[:3])
    CleAPI.objects.create(
        partenaire=partenaire,
        prefixe=prefixe,
        hash_cle=hash_cle,
        statut=StatutCleAPI.ACTIVE,
    )
    return partenaire, cle_complete


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def partenaire(api_client):
    """Partenaire authentifié par clé API (Kivu Shop)."""
    partenaire, cle = _creer_partenaire(
        "kivushop@test.com", "Kivu Shop", "https://kivushop.cd/webhook"
    )
    api_client.credentials(HTTP_X_API_KEY=cle)
    return partenaire


@pytest.fixture
def partenaire_sans_webhook():
    """Partenaire dont l'``url_webhook`` est vide."""
    partenaire, _cle = _creer_partenaire("gomatech@test.com", "Goma Tech", None)
    return partenaire


@pytest.fixture
def autre_partenaire():
    """Second partenaire (Mama Mode) pour tester le cloisonnement."""
    partenaire, _cle = _creer_partenaire(
        "mamamode@test.com", "Mama Mode", "https://mamamode.cd/webhook"
    )
    return partenaire


@pytest.fixture
def course_model():
    return apps.get_model("courses", "Course")


@pytest.fixture
def zone_model():
    return apps.get_model("logistics", "Zone")


@pytest.fixture
def creer_course_factory(course_model, zone_model):
    """Fabrique une course rattachée à un partenaire donné."""

    def _make(partenaire, statut="creee", prix=Decimal("4.00"), **kwargs):
        zone_depart, _ = zone_model.objects.get_or_create(nom="Goma")
        zone_arrivee, _ = zone_model.objects.get_or_create(nom="Kinshasa")
        return course_model.objects.create(
            partenaire=partenaire,
            zone_depart=zone_depart,
            zone_arrivee=zone_arrivee,
            destinataire_nom="Amani K.",
            destinataire_tel="+243970000000",
            description_colis="Robe en carton",
            prix_usd=prix,
            statut=statut,
            **kwargs,
        )

    return _make
