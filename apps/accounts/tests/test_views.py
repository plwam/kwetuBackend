import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.enums import Role, StatutCleAPI
from apps.accounts.models import CleAPI, Livreur, Partenaire

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
def livreur(livreur_user):
    return Livreur.objects.create(user=livreur_user)


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
class TestAuthEndpoints:
    def test_login_admin(self, api_client, admin_user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["role"] == "ADMIN"

    def test_login_partenaire(self, api_client, partenaire_user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "partenaire@test.com", "password": "pass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["role"] == "PARTENAIRE"

    def test_login_livreur(self, api_client, livreur_user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "livreur@test.com", "password": "pass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["role"] == "LIVREUR"

    def test_login_compte_desactive(self, api_client, admin_user):
        admin_user.actif = False
        admin_user.save()
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token(self, api_client, admin_user):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        refresh = login_resp.data["refresh"]
        response = api_client.post(
            "/api/v1/auth/refresh/", {"refresh": refresh}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_me_endpoint(self, api_client, admin_user):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "admin@test.com"

    def test_me_without_token(self, api_client):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout(self, api_client, admin_user):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        refresh = login_resp.data["refresh"]
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.post(
            "/api/v1/auth/logout/", {"refresh": refresh}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAdminPartenaireEndpoints:
    def test_lister_partenaires_admin(self, api_client, admin_user, partenaire):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.get("/api/v1/admin/partenaires/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_lister_partenaires_partenaire_interdit(
        self, api_client, partenaire_user, partenaire
    ):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "partenaire@test.com", "password": "pass123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.get("/api/v1/admin/partenaires/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_creer_partenaire(self, api_client, admin_user):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.post(
            "/api/v1/admin/partenaires/",
            {
                "email": "newpartenaire@test.com",
                "nom": "Nouveau",
                "prenom": "Partenaire",
                "telephone": "+243555555555",
                "mot_de_passe": "pass123",
                "nom_boutique": "Nouvelle Boutique",
                "url_webhook": "https://new.com/webhook",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "cle_api" in response.data
        assert response.data["cle_api"] is not None

    def test_generer_cle_api(self, api_client, admin_user, partenaire):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.post(
            f"/api/v1/admin/partenaires/{partenaire.id}/generer-cle/"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "cle_complete" in response.data


@pytest.mark.django_db
class TestAdminLivreurEndpoints:
    def test_lister_livreurs_admin(self, api_client, admin_user, livreur):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.get("/api/v1/admin/livreurs/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_creer_livreur(self, api_client, admin_user):
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admin@test.com", "password": "admin123"},
            format="json",
        )
        access = login_resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.post(
            "/api/v1/admin/livreurs/",
            {
                "email": "newlivreur@test.com",
                "nom": "Nouveau",
                "prenom": "Livreur",
                "telephone": "+243444444444",
                "mot_de_passe": "pass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestCleAPIAuthentication:
    def test_auth_avec_cle_api_valide(self, api_client, cle_api, partenaire):
        _cle_api_obj, cle_complete = cle_api
        api_client.credentials(HTTP_X_API_KEY=cle_complete)
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_auth_avec_cle_api_invalide(self, api_client):
        api_client.credentials(HTTP_X_API_KEY="pk_live_invalide_secret")
        response = api_client.get("/api/v1/partenaire/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
