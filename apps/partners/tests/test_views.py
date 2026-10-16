from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.accounts.enums import Role
from apps.logistics.exceptions import TarifIntrouvable as TarifIntrouvableLogistics

pytestmark = pytest.mark.django_db

User = get_user_model()

URL_LISTE = "/api/v1/partenaire/courses/"


def _payload(zone_depart, zone_arrivee):
    return {
        "zone_depart": zone_depart.id,
        "zone_arrivee": zone_arrivee.id,
        "destinataire_nom": "Amani K.",
        "destinataire_tel": "+243970000000",
        "description_colis": "Robe en carton",
    }


class TestAuthentification:
    def test_sans_cle_api(self, api_client):
        response = api_client.get(URL_LISTE)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_avec_cle_api_invalide(self, api_client):
        api_client.credentials(HTTP_X_API_KEY="pk_live_inconnu_secret_inconnu")
        response = api_client.get(URL_LISTE)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jeton_livreur_refuse(self, api_client, zone_model):
        livreur = User.objects.create_user(
            email="livreur@test.com",
            nom="Martin",
            prenom="Pierre",
            telephone="+243770000000",
            role=Role.LIVREUR,
            password="pass123",
        )
        api_client.force_authenticate(user=livreur)
        response = api_client.get(URL_LISTE)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestCreation:
    @patch("apps.logistics.services.calculer_prix", return_value=Decimal("4.00"))
    def test_creation_reussie(
        self, mock_prix, api_client, partenaire, zone_model, course_model
    ):
        zone_depart = zone_model.objects.create(nom="Goma")
        zone_arrivee = zone_model.objects.create(nom="Kinshasa")

        response = api_client.post(
            URL_LISTE, _payload(zone_depart, zone_arrivee), format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["prix_usd"] == "4.00"
        assert response.data["statut"] == "creee"
        assert response.data["paye"] is False
        # La référence est générée par le modèle `Course` (format GM-####).
        assert response.data["reference"].startswith("GM-")
        assert course_model.objects.count() == 1

    @patch("apps.logistics.services.calculer_prix", return_value=Decimal("4.00"))
    def test_prix_et_statut_envoyes_sont_ignores(
        self, mock_prix, api_client, partenaire, zone_model, course_model
    ):
        zone_depart = zone_model.objects.create(nom="Goma")
        zone_arrivee = zone_model.objects.create(nom="Kinshasa")
        payload = _payload(zone_depart, zone_arrivee)
        payload["prix_usd"] = "0.01"
        payload["statut"] = "livree"
        payload["paye"] = True

        response = api_client.post(URL_LISTE, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["prix_usd"] == "4.00"
        assert response.data["statut"] == "creee"
        assert response.data["paye"] is False

    @patch(
        "apps.logistics.services.calculer_prix",
        side_effect=TarifIntrouvableLogistics(),
    )
    def test_creation_sans_tarif(self, mock_prix, api_client, partenaire, zone_model):
        zone_depart = zone_model.objects.create(nom="Goma")
        zone_arrivee = zone_model.objects.create(nom="Kinshasa")

        response = api_client.post(
            URL_LISTE, _payload(zone_depart, zone_arrivee), format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_creation_champ_obligatoire_manquant(
        self, api_client, partenaire, zone_model
    ):
        zone_depart = zone_model.objects.create(nom="Goma")
        zone_arrivee = zone_model.objects.create(nom="Kinshasa")
        payload = _payload(zone_depart, zone_arrivee)
        del payload["destinataire_nom"]

        response = api_client.post(URL_LISTE, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCloisonnement:
    def test_liste_ne_renvoie_que_les_courses_du_partenaire(
        self, api_client, partenaire, autre_partenaire, creer_course_factory
    ):
        creer_course_factory(partenaire)
        creer_course_factory(autre_partenaire)

        # La clé API du partenaire courant reste active dans le client.
        response = api_client.get(URL_LISTE)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"]

    def test_detail_de_sa_propre_course(
        self, api_client, partenaire, creer_course_factory
    ):
        course = creer_course_factory(partenaire)

        response = api_client.get(f"{URL_LISTE}{course.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["reference"] == course.reference
        assert response.data["historique"] == []

    def test_detail_de_la_course_d_un_autre_partenaire(
        self, api_client, partenaire, autre_partenaire, creer_course_factory
    ):
        course = creer_course_factory(autre_partenaire)

        response = api_client.get(f"{URL_LISTE}{course.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_detail_course_inexistante(self, api_client, partenaire):
        response = api_client.get(f"{URL_LISTE}99999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAnnulation:
    def test_annuler_sa_course_creee(
        self, api_client, partenaire, creer_course_factory
    ):
        course = creer_course_factory(partenaire, statut="creee")

        response = api_client.post(f"{URL_LISTE}{course.id}/annuler/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["statut"] == "annulee"

    def test_annuler_sa_course_acceptee(
        self, api_client, partenaire, creer_course_factory
    ):
        course = creer_course_factory(partenaire, statut="acceptee")

        response = api_client.post(f"{URL_LISTE}{course.id}/annuler/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["statut"] == "annulee"

    def test_annuler_course_recuperee_impossible(
        self, api_client, partenaire, creer_course_factory
    ):
        course = creer_course_factory(partenaire, statut="recuperee")

        response = api_client.post(f"{URL_LISTE}{course.id}/annuler/")

        assert response.status_code == status.HTTP_409_CONFLICT
        course.refresh_from_db()
        assert course.statut == "recuperee"

    def test_annuler_la_course_d_un_autre_partenaire(
        self, api_client, partenaire, autre_partenaire, creer_course_factory
    ):
        course = creer_course_factory(autre_partenaire, statut="creee")

        response = api_client.post(f"{URL_LISTE}{course.id}/annuler/")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSuiviStatut:
    def test_suivre_sa_course(self, api_client, partenaire, creer_course_factory):
        course = creer_course_factory(partenaire, statut="acceptee")

        response = api_client.get(f"{URL_LISTE}{course.id}/statut/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["reference"] == course.reference
        assert response.data["statut"] == "acceptee"
