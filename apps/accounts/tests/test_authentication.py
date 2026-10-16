import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.enums import Role, StatutCleAPI
from apps.accounts.models import CleAPI, Partenaire

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="admin@test.com",
        nom="Admin",
        prenom="Super",
        telephone="+243999999999",
        password="admin123",
    )


@pytest.fixture
def partenaire_user():
    return User.objects.create_user(
        email="partenaire@test.com",
        nom="Dupont",
        prenom="Jean",
        telephone="+243888888888",
        role=Role.PARTENAIRE,
        password="pass123",
    )


@pytest.fixture
def livreur_user():
    return User.objects.create_user(
        email="livreur@test.com",
        nom="Martin",
        prenom="Pierre",
        telephone="+243777777777",
        role=Role.LIVREUR,
        password="pass123",
    )


@pytest.fixture
def partenaire(partenaire_user):
    return Partenaire.objects.create(
        user=partenaire_user,
        nom_boutique="Boutique Test",
        url_webhook="https://test.com/webhook",
    )


@pytest.fixture
def cle_api(partenaire):
    cle_complete, hash_cle = CleAPI.generer_cle()
    parts = cle_complete.split("_")
    prefixe = "_".join(parts[:3])
    return (
        CleAPI.objects.create(
            partenaire=partenaire,
            prefixe=prefixe,
            hash_cle=hash_cle,
            statut=StatutCleAPI.ACTIVE,
        ),
        cle_complete,
    )


@pytest.mark.django_db
class TestAuthentificationCleAPI:
    def test_authentification_cle_valide(self, api_client, cle_api, partenaire):
        _cle_api_obj, cle_complete = cle_api
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_authentification_cle_invalide(self, api_client):
        api_client.credentials(HTTP_X_API_KEY="pk_live_invalide_secret")
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentification_cle_revoquee(self, api_client, cle_api):
        cle_api_obj, cle_complete = cle_api
        cle_api_obj.revoquer()
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentification_cle_partenaire_inactif(
        self, api_client, cle_api, partenaire
    ):
        _cle_api_obj, cle_complete = cle_api
        partenaire.actif = False
        partenaire.save()
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentification_cle_user_inactif(
        self, api_client, cle_api, partenaire_user
    ):
        _cle_api_obj, cle_complete = cle_api
        partenaire_user.actif = False
        partenaire_user.save()
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cle_api_pas_admin(self, api_client, cle_api):
        _cle_api_obj, cle_complete = cle_api
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/admin/partenaires/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cle_api_pas_livreur(self, api_client, cle_api):
        """Une clé API partenaire n'ouvre pas l'espace livreur (JWT uniquement)."""
        _cle_api_obj, cle_complete = cle_api
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/livreur/courses/disponibles/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
