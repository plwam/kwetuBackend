from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Livreur, Partenaire, User
from apps.courses.enums import StatutCourse
from apps.courses.models import Course
from apps.logistics.models import Zone

from apps.accounts.models import User, Role   # adapte selon tes imports

def creer_utilisateur(
    email="user@example.com",
    nom="Nom",
    prenom="Prenom",
    telephone="+243900000000",
    password="x",
    **extra,
):
    return User.objects.create_user(
        email=email,
        nom=nom,
        prenom=prenom,
        telephone=telephone,
        password=password,
        **extra,
    )


class TestAPIAdminCourses(APITestCase):

    def setUp(self):
        self.admin = creer_utilisateur(email="admin@example.com", role="ADMIN")

        self.autre = creer_utilisateur(email="part@example.com", role="PARTENAIRE")
        self.partenaire = Partenaire.objects.create(user=self.autre, nom_boutique="Boutique")
        user_l = creer_utilisateur(email="liv@example.com", role="LIVREUR")        
        self.livreur = Livreur.objects.create(user=user_l, disponible=True, actif=True, verifie=True)
        zone_a = Zone.objects.create(nom="Zone A")
        zone_b = Zone.objects.create(nom="Zone B")
        self.course = Course.objects.create(
            reference="GM-0001",
            partenaire=self.partenaire,
            zone_depart=zone_a,
            zone_arrivee=zone_b,
            destinataire_nom="Client",
            destinataire_tel="000",
            description_colis="Colis",
            prix_usd=Decimal("5.00"),
        )

    def test_non_authentifie_est_refuse(self):
        reponse = self.client.get("/api/v1/courses/admin/courses/")
        self.assertIn(
            reponse.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_partenaire_est_refuse(self):
        self.client.force_authenticate(self.autre)
        reponse = self.client.get("/api/v1/courses/admin/courses/")
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_liste_les_courses(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.get("/api/v1/courses/admin/courses/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertTrue(reponse.data["success"])
        self.assertEqual(reponse.data["data"]["count"], 1)

    def test_filtre_par_statut(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.get("/api/v1/courses/admin/courses/?statut=livree")
        self.assertEqual(reponse.data["data"]["count"], 0)

    def test_detail_contient_l_historique(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.get(f"/api/v1/courses/admin/courses/{self.course.id}/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIn("historique", reponse.data["data"])
        self.assertNotIn("code_confirmation", reponse.data["data"])

    def test_dashboard(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.get("/api/v1/courses/admin/dashboard/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["data"]["total"], 1)

    def test_assignation_reussie(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.post(
            f"/api/v1/courses/admin/courses/{self.course.id}/assigner/",
            {"livreur_id": self.livreur.id},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["data"]["statut"], StatutCourse.ACCEPTEE)

    def test_assignation_refusee_pour_un_partenaire(self):
        self.client.force_authenticate(self.autre)
        reponse = self.client.post(
            f"/api/v1/courses/admin/courses/{self.course.id}/assigner/",
            {"livreur_id": self.livreur.id},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

    def test_assignation_course_inexistante(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.post(
            "/api/v1/courses/admin/courses/99999/assigner/",
            {"livreur_id": self.livreur.id},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(reponse.data["error"]["code"], "course_introuvable")

    def test_assignation_sans_livreur_id(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.post(
            f"/api/v1/courses/admin/courses/{self.course.id}/assigner/", {}, format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)