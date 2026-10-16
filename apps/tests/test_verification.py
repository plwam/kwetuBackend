"""Tests des nouvelles fonctionnalités compte/livreur :

    - signup autonome d'un livreur ;
    - complétion du profil ;
    - documents de vérification (admin + livreur) et formats autorisés ;
    - vérification automatique / rejet / bascule manuelle admin ;
    - blocage des activités d'un livreur non vérifié ;
    - dashboards par espace (admin, partenaire, livreur) ;
    - actions partenaire par clé API.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.enums import Role, StatutDocument
from apps.accounts.models import Livreur, Partenaire
from apps.accounts.services import generer_cle_api
from apps.courses.enums import StatutCourse
from apps.courses.models import Course
from apps.logistics.models import Tarif, Zone

User = get_user_model()

MOT_DE_PASSE = "MotDePasse123!"

URL_SIGNUP = "/api/v1/auth/signup/livreur/"
URL_LOGIN = "/api/v1/auth/login/"
URL_ADMIN_LIVREURS = "/api/v1/auth/admin/livreurs/"
URL_ADMIN_PARTENAIRES = "/api/v1/auth/admin/partenaires/"
URL_ADMIN_DASHBOARD = "/api/v1/admin/dashboard/"
URL_ADMIN_DOC_REQUIS = "/api/v1/admin/documents-requis/"
URL_ADMIN_DOCUMENTS = "/api/v1/admin/documents/"
URL_PARTENAIRE_DASHBOARD = "/api/v1/partenaire/dashboard/"
URL_COURSES_PARTENAIRE = "/api/v1/partenaire/courses/"
URL_LIVREUR_PROFIL = "/api/v1/livreur/profil/"
URL_LIVREUR_DOCUMENTS = "/api/v1/livreur/documents/"
URL_LIVREUR_DASHBOARD = "/api/v1/livreur/dashboard/"
URL_LIVREUR_DISPONIBLES = "/api/v1/livreur/courses/disponibles/"
URL_COURSES_ADMIN = "/api/v1/courses/admin/courses/"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    yield


def client_pour(user):
    jeton = RefreshToken.for_user(user).access_token
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
    return client


def client_jeton(access):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def inscrire(email="libre@test.com"):
    reponse = APIClient().post(
        URL_SIGNUP,
        {"email": email, "password": MOT_DE_PASSE, "confirmation": MOT_DE_PASSE},
        format="json",
    )
    return reponse


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
        user=partenaire_user, nom_boutique="Boutique Test"
    )


@pytest.fixture
def partenaire_client(partenaire_user):
    return client_pour(partenaire_user)


@pytest.fixture
def zones():
    return Zone.objects.create(nom="Himbi"), Zone.objects.create(nom="Birere")


@pytest.fixture
def tarif(zones):
    depart, arrivee = zones
    return Tarif.objects.create(
        zone_depart=depart, zone_arrivee=arrivee, prix_usd=Decimal("5.00")
    )


def creer_course(partenaire, zone_depart, zone_arrivee, **overrides):
    valeurs = {
        "partenaire": partenaire,
        "zone_depart": zone_depart,
        "zone_arrivee": zone_arrivee,
        "destinataire_nom": "Amani K.",
        "destinataire_tel": "+243970000099",
        "description_colis": "Colis",
        "prix_usd": Decimal("4.00"),
        "statut": StatutCourse.CREEE,
    }
    valeurs.update(overrides)
    return Course.objects.create(**valeurs)


class TestSignupLivreur:
    def test_signup_succes(self):
        reponse = inscrire()
        assert reponse.status_code == 201
        assert {"access", "refresh", "user"} <= set(reponse.data)
        assert reponse.data["user"]["role"] == Role.LIVREUR
        assert reponse.data["user"]["nom"] == ""
        assert Livreur.objects.filter(user__email="libre@test.com").exists()
        livreur = Livreur.objects.get(user__email="libre@test.com")
        assert livreur.verifie is False
        assert livreur.actif is True

    def test_signup_email_deja_utilise(self):
        inscrire()
        reponse = inscrire()
        assert reponse.status_code == 400

    def test_signup_confirmation_differente(self):
        reponse = APIClient().post(
            URL_SIGNUP,
            {"email": "x@test.com", "password": MOT_DE_PASSE, "confirmation": "Autre123!"},
            format="json",
        )
        assert reponse.status_code == 400

    def test_signup_mot_de_passe_faible(self):
        reponse = APIClient().post(
            URL_SIGNUP, {"email": "y@test.com", "password": "123", "confirmation": "123"},
            format="json",
        )
        assert reponse.status_code == 400

    def test_signup_puis_login(self):
        inscrire()
        reponse = APIClient().post(
            URL_LOGIN, {"email": "libre@test.com", "password": MOT_DE_PASSE}, format="json"
        )
        assert reponse.status_code == 200
        assert reponse.data["user"]["role"] == Role.LIVREUR


class TestProfilLivreur:
    def test_profil_initial_incomplet(self):
        access = inscrire().data["access"]
        reponse = client_jeton(access).get(URL_LIVREUR_PROFIL)
        assert reponse.status_code == 200
        assert reponse.data["verifie"] is False
        assert reponse.data["profil_complet"] is False
        assert reponse.data["documents"] == []

    def test_completer_profil(self):
        access = inscrire().data["access"]
        client = client_jeton(access)
        reponse = client.patch(
            URL_LIVREUR_PROFIL,
            {"nom": "Kabila", "prenom": "Joseph", "telephone": "+243970000123"},
            format="json",
        )
        assert reponse.status_code == 200
        assert reponse.data["nom"] == "Kabila"
        assert reponse.data["profil_complet"] is True

    def test_profil_sans_jeton(self):
        assert APIClient().get(URL_LIVREUR_PROFIL).status_code == 401

    def test_profil_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_LIVREUR_PROFIL).status_code == 403


class TestDocumentsLivreur:
    def _uploads(self, document_requis_id, nom="cni.pdf", contenu=b"%PDF-1.4", mime="application/pdf"):
        fichier = SimpleUploadedFile(nom, contenu, content_type=mime)
        return {"document_requis": document_requis_id, "fichier": fichier}

    def test_liste_documents_manquants(self, admin_client):
        admin_client.post(
            URL_ADMIN_DOC_REQUIS,
            {"nom": "Carte d'identité", "obligatoire": True},
            format="json",
        )
        access = inscrire().data["access"]
        reponse = client_jeton(access).get(URL_LIVREUR_DOCUMENTS)
        assert reponse.status_code == 200
        assert reponse.data["verifie"] is False
        assert len(reponse.data["documents"]) == 1
        assert reponse.data["documents"][0]["statut"] == "manquant"

    def test_upload_pdf(self, admin_client):
        requise = admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "CNI", "obligatoire": True}, format="json"
        ).data
        access = inscrire().data["access"]
        reponse = client_jeton(access).post(
            URL_LIVREUR_DOCUMENTS, self._uploads(requise["id"]), format="multipart"
        )
        assert reponse.status_code == 201
        assert reponse.data["statut"] == StatutDocument.EN_ATTENTE

    def test_upload_svg_refuse(self, admin_client):
        requise = admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "CNI", "obligatoire": True}, format="json"
        ).data
        access = inscrire().data["access"]
        reponse = client_jeton(access).post(
            URL_LIVREUR_DOCUMENTS,
            self._uploads(requise["id"], nom="bad.svg", contenu=b"<svg/>", mime="image/svg+xml"),
            format="multipart",
        )
        assert reponse.status_code == 400

    def test_upload_extension_refusee(self, admin_client):
        requise = admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "CNI", "obligatoire": True}, format="json"
        ).data
        access = inscrire().data["access"]
        reponse = client_jeton(access).post(
            URL_LIVREUR_DOCUMENTS,
            self._uploads(requise["id"], nom="fichier.txt", contenu=b"hello", mime="text/plain"),
            format="multipart",
        )
        assert reponse.status_code == 400

    def test_upload_trop_volumineux(self, admin_client, settings):
        settings.TAILLE_MAX_DOCUMENT_OCTETS = 10
        requise = admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "CNI", "obligatoire": True}, format="json"
        ).data
        access = inscrire().data["access"]
        reponse = client_jeton(access).post(
            URL_LIVREUR_DOCUMENTS,
            self._uploads(requise["id"], contenu=b"x" * 100),
            format="multipart",
        )
        assert reponse.status_code == 400

    def test_documents_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_LIVREUR_DOCUMENTS).status_code == 403


class TestVerification:
    def _soumettre(self, admin_client, email="libre@test.com"):
        requise = admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "CNI", "obligatoire": True}, format="json"
        ).data
        access = inscrire(email).data["access"]
        client = client_jeton(access)
        fichier = SimpleUploadedFile("cni.pdf", b"%PDF-1.4", content_type="application/pdf")
        document = client.post(
            URL_LIVREUR_DOCUMENTS,
            {"document_requis": requise["id"], "fichier": fichier},
            format="multipart",
        ).data
        return client, document

    def test_validation_rend_le_livreur_verifie(self, admin_client):
        client, document = self._soumettre(admin_client)

        liste = admin_client.get(URL_ADMIN_DOCUMENTS)
        assert liste.data["count"] == 1

        valide = admin_client.post(
            f"{URL_ADMIN_DOCUMENTS}{document['id']}/valider/",
            {"commentaire": "OK"},
            format="json",
        )
        assert valide.status_code == 200
        assert valide.data["statut"] == StatutDocument.VALIDE

        profil = client.get(URL_LIVREUR_PROFIL)
        assert profil.data["verifie"] is True
        assert Livreur.objects.get(user__email="libre@test.com").verifie is True

    def test_rejet_laisse_le_livreur_non_verifie(self, admin_client):
        client, document = self._soumettre(admin_client)
        admin_client.post(f"{URL_ADMIN_DOCUMENTS}{document['id']}/valider/", {}, format="json")
        assert client.get(URL_LIVREUR_PROFIL).data["verifie"] is True

        rejet = admin_client.post(
            f"{URL_ADMIN_DOCUMENTS}{document['id']}/rejeter/",
            {"commentaire": "Illisible"},
            format="json",
        )
        assert rejet.status_code == 200
        assert rejet.data["statut"] == StatutDocument.REJETE
        assert client.get(URL_LIVREUR_PROFIL).data["verifie"] is False

    def test_documents_optionnels_ne_bloquent_pas(self, admin_client):
        obligatoire = admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "CNI", "obligatoire": True}, format="json"
        ).data
        admin_client.post(
            URL_ADMIN_DOC_REQUIS, {"nom": "Photo", "obligatoire": False}, format="json"
        )
        access = inscrire("opt@test.com").data["access"]
        client = client_jeton(access)
        fichier = SimpleUploadedFile("cni.pdf", b"%PDF-1.4", content_type="application/pdf")
        document = client.post(
            URL_LIVREUR_DOCUMENTS,
            {"document_requis": obligatoire["id"], "fichier": fichier},
            format="multipart",
        ).data
        admin_client.post(f"{URL_ADMIN_DOCUMENTS}{document['id']}/valider/", {}, format="json")
        assert client.get(URL_LIVREUR_PROFIL).data["verifie"] is True

    def test_admin_bascule_manuelle(self, admin_client):
        cree = admin_client.post(
            URL_ADMIN_LIVREURS,
            {
                "email": "manuel@test.com",
                "nom": "M",
                "prenom": "L",
                "telephone": "+243970000555",
                "mot_de_passe": MOT_DE_PASSE,
            },
            format="json",
        ).data
        assert cree["verifie"] is True

        bascule = admin_client.patch(
            f"{URL_ADMIN_LIVREURS}{cree['id']}/", {"verifie": False}, format="json"
        )
        assert bascule.status_code == 200
        assert Livreur.objects.get(id=cree["id"]).verifie is False

        rebascule = admin_client.patch(
            f"{URL_ADMIN_LIVREURS}{cree['id']}/", {"verifie": True}, format="json"
        )
        assert rebascule.status_code == 200
        assert Livreur.objects.get(id=cree["id"]).verifie is True


class TestBlocageNonVerifie:
    def test_activites_bloquees(self, zones):
        access = inscrire().data["access"]
        reponse = client_jeton(access).get(URL_LIVREUR_DISPONIBLES)
        assert reponse.status_code == 403
        assert reponse.data["error"]["code"] == "compte_non_verifie"

    def test_dashboard_accessible(self):
        access = inscrire().data["access"]
        reponse = client_jeton(access).get(URL_LIVREUR_DASHBOARD)
        assert reponse.status_code == 200
        assert reponse.data["data"]["verifie"] is False

    def test_assignation_refusee(self, admin_client, partenaire, zones):
        inscrire()
        livreur = Livreur.objects.get(user__email="libre@test.com")
        course = creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.post(
            f"{URL_COURSES_ADMIN}{course.id}/assigner/",
            {"livreur_id": livreur.id},
            format="json",
        )
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "livreur_non_eligible"


class TestDashboards:
    def test_admin(self, admin_client, partenaire, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.get(URL_ADMIN_DASHBOARD)
        assert reponse.status_code == 200
        donnees = reponse.data["data"]
        assert donnees["courses"]["total"] == 1
        assert "partenaires" in donnees
        assert "livreurs" in donnees
        assert "documents_en_attente" in donnees

    def test_admin_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_ADMIN_DASHBOARD).status_code == 403

    def test_admin_refuse_anonyme(self):
        assert APIClient().get(URL_ADMIN_DASHBOARD).status_code == 401

    def test_partenaire(self, partenaire, partenaire_client, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = partenaire_client.get(URL_PARTENAIRE_DASHBOARD)
        assert reponse.status_code == 200
        assert reponse.data["data"]["courses"]["total"] == 1
        assert "depenses_usd" in reponse.data["data"]

    def test_partenaire_par_cle_api(self, partenaire, zones):
        _cle, cle_complete = generer_cle_api(partenaire)
        creer_course(partenaire, zones[0], zones[1])
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=cle_complete)
        reponse = client.get(URL_PARTENAIRE_DASHBOARD)
        assert reponse.status_code == 200
        assert reponse.data["data"]["courses"]["total"] == 1

    def test_livreur(self):
        access = inscrire().data["access"]
        reponse = client_jeton(access).get(URL_LIVREUR_DASHBOARD)
        assert reponse.status_code == 200
        donnees = reponse.data["data"]
        assert donnees["verifie"] is False
        assert donnees["courses"]["disponibles"] == 0

    def test_livreur_refuse_partenaire(self, partenaire_client):
        assert partenaire_client.get(URL_LIVREUR_DASHBOARD).status_code == 403


class TestPartenaireCleAPI:
    def test_creation_course_par_cle_api(self, partenaire, zones, tarif):
        _cle, cle_complete = generer_cle_api(partenaire)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=cle_complete)
        reponse = client.post(
            URL_COURSES_PARTENAIRE,
            {
                "zone_depart": zones[0].id,
                "zone_arrivee": zones[1].id,
                "destinataire_nom": "Amani",
                "destinataire_tel": "+243970000099",
                "description_colis": "Colis",
            },
            format="json",
        )
        assert reponse.status_code == 201
        assert reponse.data["statut"] == "creee"


class TestDocsAPI:
    def test_schema_accessible(self):
        assert APIClient().get("/api/schema/").status_code == 200

    def test_documents_requis_reserve_admin(self, partenaire_client):
        assert partenaire_client.get(URL_ADMIN_DOC_REQUIS).status_code == 403

    def test_documents_requis_anonyme(self):
        assert APIClient().get(URL_ADMIN_DOC_REQUIS).status_code == 401


class TestAdminGestionComptes:
    def _creer_livreur(self, admin_client, email="livreur.admin@test.com"):
        return admin_client.post(
            URL_ADMIN_LIVREURS,
            {
                "email": email,
                "nom": "L",
                "prenom": "V",
                "telephone": "+243910000000",
                "mot_de_passe": MOT_DE_PASSE,
            },
            format="json",
        )

    def test_email_duplique_partenaire(self, admin_client, partenaire_user):
        reponse = admin_client.post(
            URL_ADMIN_PARTENAIRES,
            {
                "email": partenaire_user.email,
                "nom": "D",
                "prenom": "J",
                "telephone": "+243900000003",
                "mot_de_passe": MOT_DE_PASSE,
                "nom_boutique": "Autre Boutique",
            },
            format="json",
        )
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "email_deja_utilise"

    def test_email_duplique_livreur(self, admin_client):
        assert self._creer_livreur(admin_client).status_code == 201
        reponse = self._creer_livreur(admin_client)
        assert reponse.status_code == 400
        assert reponse.data["error"]["code"] == "email_deja_utilise"

    def test_suppression_partenaire_avec_course(self, admin_client, partenaire, zones):
        creer_course(partenaire, zones[0], zones[1])
        reponse = admin_client.delete(f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/")
        assert reponse.status_code == 409
        assert reponse.data["code"] == "suppression_impossible"

    def test_suppression_livreur_avec_course(self, admin_client, partenaire, zones):
        livreur = self._creer_livreur(admin_client).data
        objet = Livreur.objects.get(id=livreur["id"])
        creer_course(
            partenaire, zones[0], zones[1], livreur=objet, statut=StatutCourse.ACCEPTEE
        )
        reponse = admin_client.delete(f"{URL_ADMIN_LIVREURS}{livreur['id']}/")
        assert reponse.status_code == 409
        assert reponse.data["code"] == "suppression_impossible"

    def test_desactivation_reactivation_partenaire(self, admin_client, partenaire):
        reponse = admin_client.post(
            f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/desactiver/"
        )
        assert reponse.status_code == 200
        assert reponse.data["actif"] is False
        partenaire.refresh_from_db()
        assert partenaire.actif is False
        assert partenaire.user.actif is False

        reponse = admin_client.post(
            f"{URL_ADMIN_PARTENAIRES}{partenaire.id}/reactiver/"
        )
        assert reponse.status_code == 200
        assert reponse.data["actif"] is True

    def test_desactivation_reactivation_livreur(self, admin_client):
        livreur = self._creer_livreur(admin_client).data
        reponse = admin_client.post(f"{URL_ADMIN_LIVREURS}{livreur['id']}/desactiver/")
        assert reponse.status_code == 200
        assert reponse.data["actif"] is False
        reponse = admin_client.post(f"{URL_ADMIN_LIVREURS}{livreur['id']}/reactiver/")
        assert reponse.status_code == 200
        assert reponse.data["actif"] is True
