import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.enums import Role

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def partenaire_temporaire():
    """Partenaire créé par l'admin avec mot de passe temporaire."""
    return User.objects.create_user(
        email="temp@test.com",
        nom="Dupont",
        prenom="Jean",
        telephone="+243888888888",
        role=Role.PARTENAIRE,
        password="temp1234",
        mot_de_passe_temporaire=True,
    )


def _login(api_client, email, password):
    return api_client.post(
        "/api/v1/auth/login/", {"email": email, "password": password}, format="json"
    )


URL = "/api/v1/auth/changer-mot-de-passe/"
PAYLOAD_OK = {
    "ancien_mot_de_passe": "temp1234",
    "nouveau_mot_de_passe": "NouveauMot#2026",
    "confirmation": "NouveauMot#2026",
}


@pytest.mark.django_db
class TestChangerMotDePasse:
    def test_changement_reussi(self, api_client, partenaire_temporaire):
        login = _login(api_client, "temp@test.com", "temp1234")
        assert login.data["user"]["mot_de_passe_temporaire"] is True
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = api_client.post(URL, PAYLOAD_OK, format="json")
        assert response.status_code == status.HTTP_200_OK

        partenaire_temporaire.refresh_from_db()
        assert partenaire_temporaire.mot_de_passe_temporaire is False
        assert partenaire_temporaire.check_password("NouveauMot#2026")

    def test_ancien_mot_de_passe_incorrect(self, api_client, partenaire_temporaire):
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        payload = {**PAYLOAD_OK, "ancien_mot_de_passe": "faux"}
        response = api_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sans_jwt_interdit(self, api_client, partenaire_temporaire):
        response = api_client.post(URL, PAYLOAD_OK, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_mot_de_passe_trop_faible(self, api_client, partenaire_temporaire):
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        payload = {
            "ancien_mot_de_passe": "temp1234",
            "nouveau_mot_de_passe": "123",
            "confirmation": "123",
        }
        response = api_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirmation_invalide(self, api_client, partenaire_temporaire):
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        payload = {**PAYLOAD_OK, "confirmation": "Different#2026"}
        response = api_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_nouveau_identique_ancien(self, api_client, partenaire_temporaire):
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        payload = {
            "ancien_mot_de_passe": "temp1234",
            "nouveau_mot_de_passe": "temp1234",
            "confirmation": "temp1234",
        }
        response = api_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_invalide_apres_changement(self, api_client, partenaire_temporaire):
        login = _login(api_client, "temp@test.com", "temp1234")
        refresh = login.data["refresh"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = api_client.post(URL, PAYLOAD_OK, format="json")
        assert response.status_code == status.HTTP_200_OK

        refresh_resp = api_client.post(
            "/api/v1/auth/refresh/", {"refresh": refresh}, format="json"
        )
        assert refresh_resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reconnexion_avec_nouveau_mot_de_passe(
        self, api_client, partenaire_temporaire
    ):
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        api_client.post(URL, PAYLOAD_OK, format="json")

        api_client.credentials()
        new_login = _login(api_client, "temp@test.com", "NouveauMot#2026")
        assert new_login.status_code == status.HTTP_200_OK
        assert new_login.data["user"]["mot_de_passe_temporaire"] is False

    def test_ancien_mot_de_passe_rejete_apres_fermeture(
        self, api_client, partenaire_temporaire
    ):
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        api_client.post(URL, PAYLOAD_OK, format="json")

        api_client.credentials()
        assert _login(api_client, "temp@test.com", "temp1234").status_code == 401

    def test_user_id_ignore_change_seulement_son_compte(
        self, api_client, partenaire_temporaire, admin_cible
    ):
        """Aucun user_id n'est accepté : impossible de cibler un autre compte."""
        login = _login(api_client, "temp@test.com", "temp1234")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        payload = {**PAYLOAD_OK, "user_id": admin_cible.id}
        response = api_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK

        admin_cible.refresh_from_db()
        assert admin_cible.check_password("admin123")
        partenaire_temporaire.refresh_from_db()
        assert partenaire_temporaire.check_password("NouveauMot#2026")

    @pytest.fixture
    def admin_cible(self):
        return User.objects.create_superuser(
            email="cible@test.com",
            nom="Cible",
            prenom="Admin",
            telephone="+243111111111",
            password="admin123",
        )
