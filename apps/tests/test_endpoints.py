"""Suite d'intégration transversale : couvre CHAQUE endpoint de l'API ``/api/v1/``.

Espaces couverts :
    - Authentification (login, refresh, me, logout, changement de mot de passe)
    - Administration partenaires / livreurs
    - Logistique (zones, tarifs, devis)
    - Espace partenaire (courses)
    - Espace livreur (courses)
    - Administration des courses (dashboard, liste, détail, assignation)

Les tests s'exécutent via ``pytest`` et touchent l'URL réelle (routeur + permissions).
"""

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.enums import Role
from apps.accounts.models import CleAPI, Livreur, Partenaire
from apps.accounts.services import generer_cle_api
from apps.courses.enums import StatutCourse
from apps.courses.models import Course
from apps.logistics.models import Tarif, Zone

User = get_user_model()

MOT_DE_PASSE = "MotDePasse123!"
CODE_CONFIRMATION = "483920"

URL_LOGIN = "/api/v1/auth/login/"
URL_REFRESH = "/api/v1/auth/refresh/"
URL_ME = "/api/v1/auth/me/"
URL_LOGOUT = "/api/v1/auth/logout/"
URL_CHANGER_MDP = "/api/v1/auth/changer-mot-de-passe/"
URL_ADMIN_PARTENAIRES = "/api/v1/auth/admin/partenaires/"
URL_ADMIN_LIVREURS = "/api/v1/auth/admin/livreurs/"
URL_ZONES = "/api/v1/logistics/admin/zones/"
URL_TARIFS = "/api/v1/logistics/admin/tarifs/"
URL_DEVIS = "/api/v1/logistics/partenaire/devis/"
URL_COURSES_PARTENAIRE = "/api/v1/partenaire/courses/"
URL_COURSES_LIVREUR = "/api/v1/livreur/courses/"
URL_HISTORIQUE_LIVREUR = "/api/v1/livreur/historique/"
URL_DASHBOARD = "/api/v1/courses/admin/dashboard/"
URL_COURSES_ADMIN = "/api/v1/courses/admin/courses/"

pytestmark = pytest.mark.django_db


def client_pour(user):
    jeton = RefreshToken.for_user(user).access_token
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
    return client


def creer_course(partenaire, zone_depart, zone_arrivee, **overrides):
    valeurs = {
        "partenaire": partenaire,
        "zone_depart": zone_depart,
        "zone_arrivee": zone_arrivee,
        "destinataire_nom": "Amani K.",
        "destinataire_tel": "+243970000099",
        "description_colis": "Colis de test",
        "prix_usd": Decimal("4.00"),
        "statut": StatutCourse.CREEE,
        "code_confirmation": CODE_CONFIRMATION,
    }
    valeurs.update(overrides)
    return Course.objects.create(**valeurs)


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="admin@test.com",
        nom="Admin",
        prenom="Super",
        telephone="+243900000000",
        password=MOT_DE_PASSE,
    )


@pytest.fixture
def admin_client(admin_user):
    return client_pour(admin_user)


@pytest.fixture
def partenaire_user():
    return User.objects.create_user(
        email="partenaire@test.com",
        nom="Dupont",
        prenom="Jean",
        telephone="+243900000001",
        role=Role.PARTENAIRE,
        password=MOT_DE_PASSE,
    )


@pytest.fixture
def partenaire(partenaire_user):
    return Partenaire.objects.create(
        user=partenaire_user,
        nom_boutique="Boutique Test",
        url_webhook="https://test.com/webhook",
    )


@pytest.fixture
def partenaire_client(partenaire_user):
    return client_pour(partenaire_user)


@pytest.fixture
def cle_api(partenaire):
    _cle, cle_complete = generer_cle_api(partenaire)
    return cle_complete


@pytest.fixture
def livreur_user():
    return User.objects.create_user(
        email="livreur@test.com",
        nom="Martin",
        prenom="Pierre",
        telephone="+243900000002",
        role=Role.LIVREUR,
        password=MOT_DE_PASSE,
    )


@pytest.fixture
def livreur(livreur_user):
    return Livreur.objects.create(
        user=livreur_user, disponible=True, actif=True, verifie=True
    )


@pytest.fixture
def livreur_client(livreur_user):
    return client_pour(livreur_user)


@pytest.fixture
def zones():
    return Zone.objects.create(nom="Himbi"), Zone.objects.create(nom="Birere")


@pytest.fixture
def tarif(zones):
    depart, arrivee = zones
    return Tarif.objects.create(
        zone_depart=depart,
        zone_arrivee=arrivee,
        prix_usd=Decimal("5.00"),
    )


class TestAuth:
    def test_login_succes(self, admin_user):
        reponse = APIClient().post(
            URL_LOGIN, {"email": "admin@test.com", "password": MOT_DE_PASSE}, format="json"
        )
        assert reponse.status_code == 200
        assert {"access", "refresh", "user"} <= set(reponse.data)
        assert reponse.data["user"]["role"] == Role.ADMIN

    def test_login_mauvais_mot_de_passe(self, admin_user):
        reponse = APIClient().post(
            URL_LOGIN, {"email": "admin@test.com", "password": "mauvais"}, format="json"
        )
        assert reponse.status_code == 401

    def test_login_compte_desactive(self):
        User.objects.create_user(
            email="off@test.com",
            nom="Off",
            prenom="Line",
            telephone="+243900000009",
            role=Role.PARTENAIRE,
            password=MOT_DE_PASSE,
            actif=False,
        )
        reponse = APIClient().post(
            URL_LOGIN, {"email": "off@test.com", "password": MOT_DE_PASSE}, format="json"
        )
        assert reponse.status_code == 400

    def test_refresh(self, admin_user):
        refresh = str(RefreshToken.for_user(admin_user))
        reponse = APIClient().post(URL_REFRESH, {"refresh": refresh}, format="json")
        assert reponse.status_code == 200
        assert "access" in reponse.data

    def test_refresh_invalide(self):
        reponse = APIClient().post(URL_REFRESH, {"refresh": "invalide"}, format="json")
        assert reponse.status_code == 401

    def test_me(self, admin_client):
        reponse = admin_client.get(URL_ME)
        assert reponse.status_code == 200
        assert reponse.data["email"] == "admin@test.com"

    def test_me_sans_jeton(self):
        assert APIClient().get(URL_ME).status_code == 401

    def test_logout(self, admin_client, admin_user):
        refresh = str(RefreshToken.for_user(admin_user))
        reponse = admin_client.post(URL_LOGOUT, {"refresh": refresh}, format="json")
        assert reponse.status_code == 200

    def test_logout_sans_refresh(self, admin_client):
        reponse = admin_client.post(URL_LOGOUT, {}, format="json")
        assert reponse.status_code == 400

    def test_logout_refresh_invalide(self, admin_client):
        reponse = admin_client.post(URL_LOGOUT, {"refresh": "nope"}, format="json")
        assert reponse.status_code == 400

    def test_changer_mot_de_passe(self, admin_user):
        reponse = client_pour(admin_user).post(
            URL_CHANGER_MDP,
            {
                "ancien_mot_de_passe": MOT_DE_PASSE,
                "nouveau_mot_de_passe": "NouveauSecret123!",
                "confirmation": "NouveauSecret123!",
            },
            format="json",
        )
        assert reponse.status_code == 200

    def test_changer_mot_de_passe_ancien_incorrect(self, admin_user):
        reponse = client_pour(admin_user).post(
            URL_CHANGER_MDP,
            {
                "ancien_mot_de_passe": "faux",
                "nouveau_mot_de_passe": "NouveauSecret123!",
                "confirmation": "NouveauSecret123!",
            },
            format="json",
        )
        assert reponse.status_code == 400

    def test_changer_mot_de_passe_confirmation_differente(self, admin_user):
        reponse = client_pour(admin_user).post(
            URL_CHANGER_MDP,
            {
                "ancien_mot_de_passe": MOT_DE_PASSE,
                "nouveau_mot_de_passe": "NouveauSecret123!",
                "confirmation": "AutreSecret123!",
            },
            format="json",
        )
        assert reponse.status_code == 400

    def test_changer_mot_de_passe_sans_jeton(self):
        assert APIClient().post(URL_CHANGER_MDP, {}).status_code == 401


class TestAdminPartenaires:
    def test_liste(self, admin_client, partenaire):
        reponse = admin_client.get(URL_ADMIN_PARTENAIRES)
        assert reponse.status_code == 200
        assert reponse.data["count"] == 1

    def test_creation(self, admin_client):
        reponse = admin_client.post(
            URL_ADMIN_PARTENAIRES,
            {
                "email": "nouveau@test.com",
                "nom": "Nouveau",
                "prenom": "Partenaire",
                "telephone": "+243910000000",
                "mot_de_passe": MOT_DE_PASSE,
                "nom_boutique": "Nouvelle Boutique",
            },
            format="json",
        )
        assert reponse.status_code == 201
        assert reponse.data["user"]["role"] == Role.PARTENAIRE
        assert reponse.data["cle_api"].startswith("pk_live_")
        assert CleAPI.objects.filter(partenaire_id=reponse.data["id"]).exists()

    def test_detail(self, admin_client, partenaire):
        reponse = admin_client.get(f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/")
        assert reponse.status_code == 200
        assert reponse.data["id"] == partenaire.id

    def test_modification(self, admin_client, partenaire):
        reponse = admin_client.patch(
            f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/",
            {"nom_boutique": "Nouvelle Boutique"},
            format="json",
        )
        assert reponse.status_code == 200
        partenaire.refresh_from_db()
        assert partenaire.nom_boutique == "Nouvelle Boutique"

    def test_suppression(self, admin_client, partenaire):
        reponse = admin_client.delete(f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/")
        assert reponse.status_code == 204

    def test_generer_cle(self, admin_client, partenaire):
        reponse = admin_client.post(f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/generer-cle/")
        assert reponse.status_code == 201
        assert reponse.data["cle_complete"].startswith("pk_live_")

    def test_alias_admin(self, admin_client, partenaire):
        reponse = admin_client.get("/api/v1/admin/partenaires/")
        assert reponse.status_code == 200
        assert reponse.data["count"] == 1

    def test_refuse_partenaire(self, partenaire_client, partenaire):
        assert partenaire_client.get(URL_ADMIN_PARTENAIRES).status_code == 403

    def test_refuse_anonyme(self):
        assert APIClient().get(URL_ADMIN_PARTENAIRES).status_code == 401


class TestAdminLivreurs:
    def test_liste(self, admin_client, livreur):
        reponse = admin_client.get(URL_ADMIN_LIVREURS)
        assert reponse.status_code == 200
        assert reponse.data["count"] == 1

    def test_creation(self, admin_client):
        reponse = admin_client.post(
            URL_ADMIN_LIVREURS,
            {
                "email": "nouveau.livreur@test.com",
                "nom": "Nouveau",
                "prenom": "Livreur",
                "telephone": "+243920000000",
                "mot_de_passe": MOT_DE_PASSE,
            },
            format="json",
        )
        assert reponse.status_code == 201
        assert reponse.data["user"]["role"] == Role.LIVREUR

    def test_detail(self, admin_client, livreur):
        reponse = admin_client.get(f"{URL_ADMIN_LIVREURS}{livreur.id}/")
        assert reponse.status_code == 200
        assert reponse.data["id"] == livreur.id

    def test_modification(self, admin_client, livreur):
        reponse = admin_client.patch(
            f"{URL_ADMIN_LIVREURS}{livreur.id}/", {"disponible": False}, format="json"
        )
        assert reponse.status_code == 200
        livreur.refresh_from_db()
        assert livreur.disponible is False

    def test_suppression(self, admin_client, livreur):
        reponse = admin_client.delete(f"{URL_ADMIN_LIVREURS}{livreur.id}/")
        assert reponse.status_code == 204

    def test_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_ADMIN_LIVREURS).status_code == 403

    def test_refuse_anonyme(self):
        assert APIClient().get(URL_ADMIN_LIVREURS).status_code == 401


class TestZones:
    def test_liste(self, admin_client, zones):
        reponse = admin_client.get(URL_ZONES)
        assert reponse.status_code == 200
        assert reponse.data["count"] == 2

    def test_creation(self, admin_client):
        reponse = admin_client.post(URL_ZONES, {"nom": "Katindo"}, format="json")
        assert reponse.status_code == 201
        assert reponse.data["success"] is True
        assert reponse.data["data"]["nom"] == "Katindo"

    def test_creation_doublon(self, admin_client, zones):
        reponse = admin_client.post(URL_ZONES, {"nom": zones[0].nom}, format="json")
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "zone_existe"

    def test_detail(self, admin_client, zones):
        reponse = admin_client.get(f"{URL_ZONES}{zones[0].id}/")
        assert reponse.status_code == 200
        assert reponse.data["nom"] == zones[0].nom

    def test_modification(self, admin_client, zones):
        reponse = admin_client.patch(
            f"{URL_ZONES}{zones[0].id}/", {"description": "Centre-ville"}, format="json"
        )
        assert reponse.status_code == 200

    def test_suppression(self, admin_client):
        zone = Zone.objects.create(nom="Temporaire")
        reponse = admin_client.delete(f"{URL_ZONES}{zone.id}/")
        assert reponse.status_code == 204

    def test_suppression_zone_utilisee(self, admin_client, partenaire, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.delete(f"{URL_ZONES}{zones[0].id}/")
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "zone_utilisee"

    def test_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_ZONES).status_code == 403

    def test_refuse_anonyme(self):
        assert APIClient().get(URL_ZONES).status_code == 401


class TestTarifs:
    def test_liste(self, admin_client, tarif):
        reponse = admin_client.get(URL_TARIFS)
        assert reponse.status_code == 200
        assert reponse.data["count"] == 1

    def test_creation(self, admin_client, zones):
        depart, arrivee = zones
        reponse = admin_client.post(
            URL_TARIFS,
            {"zone_depart": depart.id, "zone_arrivee": arrivee.id, "prix_usd": "7.50"},
            format="json",
        )
        assert reponse.status_code == 201
        assert Decimal(reponse.data["prix_usd"]) == Decimal("7.50")

    def test_creation_doublon(self, admin_client, tarif, zones):
        depart, arrivee = zones
        reponse = admin_client.post(
            URL_TARIFS,
            {"zone_depart": depart.id, "zone_arrivee": arrivee.id, "prix_usd": "8.00"},
            format="json",
        )
        assert reponse.status_code == 400

    def test_detail(self, admin_client, tarif):
        reponse = admin_client.get(f"{URL_TARIFS}{tarif.id}/")
        assert reponse.status_code == 200
        assert reponse.data["id"] == tarif.id

    def test_modification(self, admin_client, tarif):
        reponse = admin_client.patch(
            f"{URL_TARIFS}{tarif.id}/", {"prix_usd": "9.00"}, format="json"
        )
        assert reponse.status_code == 200
        assert reponse.data["success"] is True
        assert Decimal(reponse.data["data"]["prix_usd"]) == Decimal("9.00")

    def test_suppression(self, admin_client, tarif):
        reponse = admin_client.delete(f"{URL_TARIFS}{tarif.id}/")
        assert reponse.status_code == 204

    def test_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_TARIFS).status_code == 403

    def test_refuse_anonyme(self):
        assert APIClient().get(URL_TARIFS).status_code == 401


class TestDevis:
    def test_devis_succes(self, partenaire, cle_api, tarif, zones):
        depart, arrivee = zones
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=cle_api)
        reponse = client.post(
            URL_DEVIS,
            {"zone_depart": depart.id, "zone_arrivee": arrivee.id},
            format="json",
        )
        assert reponse.status_code == 200
        assert reponse.data["success"] is True
        assert Decimal(reponse.data["data"]["prix_usd"]) == Decimal("5.00")
        assert reponse.data["data"]["zone_depart_nom"] == depart.nom

    def test_devis_sans_tarif(self, partenaire, cle_api):
        depart = Zone.objects.create(nom="Zone X")
        arrivee = Zone.objects.create(nom="Zone Y")
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=cle_api)
        reponse = client.post(
            URL_DEVIS,
            {"zone_depart": depart.id, "zone_arrivee": arrivee.id},
            format="json",
        )
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "tarif_introuvable"

    def test_devis_sans_auth(self, zones):
        reponse = APIClient().post(
            URL_DEVIS,
            {"zone_depart": zones[0].id, "zone_arrivee": zones[1].id},
            format="json",
        )
        assert reponse.status_code == 401

    def test_devis_refuse_jeton_livreur(self, livreur_user):
        reponse = client_pour(livreur_user).post(
            URL_DEVIS, {"zone_depart": 1, "zone_arrivee": 2}, format="json"
        )
        assert reponse.status_code == 401


class TestCoursesPartenaire:
    def _payload(self, zones):
        depart, arrivee = zones
        return {
            "zone_depart": depart.id,
            "zone_arrivee": arrivee.id,
            "destinataire_nom": "Amani K.",
            "destinataire_tel": "+243970000099",
            "description_colis": "Robe en carton",
        }

    def test_creation_par_jeton(self, partenaire, partenaire_client, zones, tarif):
        reponse = partenaire_client.post(
            URL_COURSES_PARTENAIRE, self._payload(zones), format="json"
        )
        assert reponse.status_code == 201
        assert reponse.data["statut"] == "creee"
        assert reponse.data["prix"] == "5.00"
        assert reponse.data["reference"]

    def test_creation_par_cle_api(self, partenaire, cle_api, zones, tarif):
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=cle_api)
        reponse = client.post(
            URL_COURSES_PARTENAIRE, self._payload(zones), format="json"
        )
        assert reponse.status_code == 201
        assert reponse.data["statut"] == "creee"

    def test_liste_cloisonnee(self, partenaire, partenaire_client, zones):
        autre_user = User.objects.create_user(
            email="autre@test.com",
            nom="Autre",
            prenom="Partenaire",
            telephone="+243930000000",
            role=Role.PARTENAIRE,
            password=MOT_DE_PASSE,
        )
        autre = Partenaire.objects.create(user=autre_user, nom_boutique="Autre Boutique")
        creer_course(partenaire, zones[0], zones[1])
        creer_course(autre, zones[0], zones[1])

        reponse = partenaire_client.get(URL_COURSES_PARTENAIRE)
        assert reponse.status_code == 200
        assert reponse.data["count"] == 1

    def test_detail(self, partenaire, partenaire_client, zones):
        course = creer_course(partenaire, zones[0], zones[1])
        reponse = partenaire_client.get(f"{URL_COURSES_PARTENAIRE}{course.id}/")
        assert reponse.status_code == 200
        assert reponse.data["reference"] == course.reference
        assert reponse.data["historique"] == []

    def test_detail_course_d_un_autre(self, partenaire, partenaire_client, zones):
        autre_user = User.objects.create_user(
            email="autre2@test.com",
            nom="Autre",
            prenom="Partenaire",
            telephone="+243930000001",
            role=Role.PARTENAIRE,
            password=MOT_DE_PASSE,
        )
        autre = Partenaire.objects.create(user=autre_user, nom_boutique="Autre Boutique 2")
        course = creer_course(autre, zones[0], zones[1])
        reponse = partenaire_client.get(f"{URL_COURSES_PARTENAIRE}{course.id}/")
        assert reponse.status_code == 403

    def test_annuler(self, partenaire, partenaire_client, zones):
        course = creer_course(partenaire, zones[0], zones[1])
        reponse = partenaire_client.post(f"{URL_COURSES_PARTENAIRE}{course.id}/annuler/")
        assert reponse.status_code == 200
        assert reponse.data["statut"] == "annulee"

    def test_statut(self, partenaire, partenaire_client, zones):
        course = creer_course(
            partenaire, zones[0], zones[1], statut=StatutCourse.ACCEPTEE
        )
        reponse = partenaire_client.get(f"{URL_COURSES_PARTENAIRE}{course.id}/statut/")
        assert reponse.status_code == 200
        assert reponse.data["statut"] == "acceptee"

    def test_sans_auth(self):
        assert APIClient().get(URL_COURSES_PARTENAIRE).status_code == 401

    def test_refuse_jeton_livreur(self, livreur_client):
        assert livreur_client.get(URL_COURSES_PARTENAIRE).status_code == 403


class TestCoursesLivreur:
    @pytest.fixture(autouse=True)
    def _vider_cache(self):
        cache.clear()
        yield
        cache.clear()

    def test_parcours_complet(self, livreur, livreur_client, partenaire, zones):
        course = creer_course(partenaire, zones[0], zones[1])

        reponse = livreur_client.get(f"{URL_COURSES_LIVREUR}disponibles/")
        assert reponse.status_code == 200
        assert reponse.data["data"]["count"] == 1

        reponse = livreur_client.post(f"{URL_COURSES_LIVREUR}{course.id}/accepter/")
        assert reponse.status_code == 200
        assert reponse.data["data"]["statut"] == "acceptee"

        reponse = livreur_client.get(f"{URL_COURSES_LIVREUR}en-cours/")
        assert reponse.status_code == 200
        assert reponse.data["data"]["count"] == 1

        reponse = livreur_client.post(f"{URL_COURSES_LIVREUR}{course.id}/recuperer/")
        assert reponse.status_code == 200
        assert reponse.data["data"]["statut"] == "recuperee"

        reponse = livreur_client.post(
            f"{URL_COURSES_LIVREUR}{course.id}/livrer/", {"code": "000000"}, format="json"
        )
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "code_incorrect"

        reponse = livreur_client.post(
            f"{URL_COURSES_LIVREUR}{course.id}/livrer/",
            {"code": CODE_CONFIRMATION},
            format="json",
        )
        assert reponse.status_code == 200
        assert reponse.data["data"]["statut"] == "livree"

        reponse = livreur_client.post(f"{URL_COURSES_LIVREUR}{course.id}/payer/")
        assert reponse.status_code == 200
        assert reponse.data["data"]["paye"] is True

        reponse = livreur_client.get(URL_HISTORIQUE_LIVREUR)
        assert reponse.status_code == 200
        assert reponse.data["data"]["resume"]["nb_livrees"] == 1

    def test_disponibles_sans_jeton(self):
        assert APIClient().get(f"{URL_COURSES_LIVREUR}disponibles/").status_code == 401

    def test_refuse_admin(self, admin_client):
        assert admin_client.get(f"{URL_COURSES_LIVREUR}disponibles/").status_code == 403

    def test_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(f"{URL_COURSES_LIVREUR}disponibles/").status_code == 403

    def test_acceptation_double(self, livreur, livreur_client, partenaire, zones):
        course = creer_course(partenaire, zones[0], zones[1])
        premier = livreur_client.post(f"{URL_COURSES_LIVREUR}{course.id}/accepter/")
        assert premier.status_code == 200

        autre = User.objects.create_user(
            email="autre.livreur@test.com",
            nom="Autre",
            prenom="Livreur",
            telephone="+243940000000",
            role=Role.LIVREUR,
            password=MOT_DE_PASSE,
        )
        Livreur.objects.create(user=autre, disponible=True, actif=True, verifie=True)
        reponse = client_pour(autre).post(f"{URL_COURSES_LIVREUR}{course.id}/accepter/")
        assert reponse.status_code == 409
        assert reponse.data["error"]["code"] == "course_non_disponible"


class TestCoursesAdmin:
    def test_dashboard(self, admin_client, partenaire, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.get(URL_DASHBOARD)
        assert reponse.status_code == 200
        assert reponse.data["data"]["total"] == 1

    def test_liste(self, admin_client, partenaire, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.get(URL_COURSES_ADMIN)
        assert reponse.status_code == 200
        assert reponse.data["data"]["count"] == 1

    def test_filtre_par_statut(self, admin_client, partenaire, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.get(f"{URL_COURSES_ADMIN}?statut=livree")
        assert reponse.status_code == 200
        assert reponse.data["data"]["count"] == 0

    def test_detail_contient_historique(self, admin_client, partenaire, zones):
        course = creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.get(f"{URL_COURSES_ADMIN}{course.id}/")
        assert reponse.status_code == 200
        assert "historique" in reponse.data["data"]
        assert "code_confirmation" not in reponse.data["data"]

    def test_assignation(self, admin_client, partenaire, livreur, zones):
        course = creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.post(
            f"{URL_COURSES_ADMIN}{course.id}/assigner/",
            {"livreur_id": livreur.id},
            format="json",
        )
        assert reponse.status_code == 200
        assert reponse.data["data"]["statut"] == StatutCourse.ACCEPTEE

    def test_assignation_course_inexistante(self, admin_client, livreur):
        reponse = admin_client.post(
            f"{URL_COURSES_ADMIN}999999/assigner/",
            {"livreur_id": livreur.id},
            format="json",
        )
        assert reponse.status_code == 404
        assert reponse.data["error"]["code"] == "course_introuvable"

    def test_assignation_sans_livreur_id(self, admin_client, partenaire, zones):
        course = creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.post(
            f"{URL_COURSES_ADMIN}{course.id}/assigner/", {}, format="json"
        )
        assert reponse.status_code == 400

    def test_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_COURSES_ADMIN).status_code == 403

    def test_refuse_anonyme(self):
        assert APIClient().get(URL_COURSES_ADMIN).status_code == 401


class TestDocumentation:
    def test_schema_openapi_accessible(self):
        assert APIClient().get("/api/schema/").status_code == 200

    def test_swagger_accessible(self):
        assert APIClient().get("/api/docs/").status_code == 200

    def test_redoc_accessible(self):
        assert APIClient().get("/api/redoc/").status_code == 200
