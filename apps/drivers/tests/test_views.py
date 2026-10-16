"""Tests des vues de drivers (API /api/v1/livreur/)."""
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.courses.enums import StatutCourse
from apps.courses.models import Course
from apps.drivers.tests.outils import (
    CODE_DE_CONFIRMATION,
    client_authentifie,
    creer_administrateur,
    creer_course,
    creer_livreur,
    creer_partenaire,
)
from apps.drivers.urls import urlpatterns as routes_drivers

class BaseTestVues(TestCase):

    def setUp(self):
        cache.clear()
        simulation = patch("apps.partners.services.envoyer_webhook")
        simulation.start()
        self.addCleanup(simulation.stop)
        self.livreur = creer_livreur("patrick")
        self.autre_livreur = creer_livreur("esther")
        self.client_livreur = client_authentifie(self.livreur.user)
    
    def url(self, nom, course=None):
        arguments = [course.id] if course is not None else []
        return reverse(f"drivers:{nom}", args=arguments)
    
    def verifier_erreur(self, reponse, statut_http, code):
        self.assertEqual(reponse.status_code, statut_http, reponse.content)
        corps = reponse.json()
        self.assertFalse(corps["success"])
        self.assertIsNone(corps["data"])
        self.assertEqual(corps["error"]["code"], code)

class TestAcces(BaseTestVues):
        
    def test_sans_jeton_401(self):
        reponse = APIClient().get(self.url("courses-disponibles"))
        self.verifier_erreur(reponse, 401, "non_authentifie")
        
    def test_cle_api_partenaire_refusee_401(self):
        reponse = APIClient().get(
               self.url("courses-disponibles"), HTTP_X_API_KEY="pk_live_abcdef"
        )
        self.verifier_erreur(reponse, 401, "non_authentifie")
        
    def test_jeton_invalide_401(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer jeton.bidon.invalide")
        reponse = client.get(self.url("courses-disponibles"))
        self.verifier_erreur(reponse, 401, "non_authentifie")
    
    def test_partenaire_refuse_403(self):
        client = client_authentifie(creer_partenaire().user)
        reponse = client.get(self.url("courses-disponibles"))
        self.verifier_erreur(reponse, 403, "acces_refuse")
        
    def test_administrateur_refuse_403(self):
        client = client_authentifie(creer_administrateur())
        reponse = client.get(self.url("courses-disponibles"))
        self.verifier_erreur(reponse, 403, "acces_refuse")
    
    def test_livreur_desactive_403(self):
        inactif = creer_livreur("inactif", actif=False)
        reponse = client_authentifie(inactif.user).get(self.url("courses-disponibles"))
        self.verifier_erreur(reponse, 403, "compte_desactive")
        
    def test_livreur_desactive_apres_emission_du_jeton(self):
          self.livreur.actif = False
          self.livreur.save()
          reponse = self.client_livreur.get(self.url("courses-disponibles"))
          self.verifier_erreur(reponse, 403, "compte_desactive")
          
    def test_aucune_route_publique(self):
         """Deny by default : chaque route de drivers refuse un appel anonyme."""
         for route in routes_drivers:
            arguments = [1] if "<int:pk>" in str(route.pattern) else []
            adresse = reverse(f"drivers:{route.name}", args=arguments)
            for methode in ("get", "post"):
                reponse = getattr(APIClient(), methode)(adresse)
                self.assertEqual(reponse.status_code, 401, f"{methode} {adresse}")

class TestLectures(BaseTestVues):
    def test_courses_disponibles_champs_limites(self):
        creer_course()
        creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.autre_livreur)
        reponse = self.client_livreur.get(self.url("courses-disponibles"))
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()["data"]
        self.assertEqual(donnees["count"], 1)
        self.assertEqual(donnees["page"], 1)
        self.assertEqual(donnees["page_size"], 20)
        course = donnees["results"][0]
        self.assertEqual(course["zone_depart"], "Himbi")
        self.assertEqual(course["prix_usd"], "4.00")
        self.assertEqual(course["statut"], "creee")
        self.assertNotIn("destinataire_tel", course)
        self.assertNotIn("partenaire_nom", course)
        self.assertNotIn("code_confirmation", course)
    
    def test_page_size_plafonnee_a_100(self):
        reponse = self.client_livreur.get(
            self.url("courses-disponibles"), {"page_size": 500}
        )
        self.assertEqual(reponse.json()["data"]["page_size"], 100)
    
    def test_page_inexistante_404(self):
        reponse = self.client_livreur.get(self.url("courses-disponibles"), {"page": 9})
        self.verifier_erreur(reponse, 404, "page_introuvable")
        
    def test_courses_en_cours_ne_montrent_que_les_miennes(self):
        creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.livreur)
        creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.autre_livreur)
        creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur)
        reponse = self.client_livreur.get(self.url("courses-en-cours"))
        resultats = reponse.json()["data"]["results"]
        
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0]["destinataire_tel"], "+243970000099")
        self.assertEqual(resultats[0]["partenaire_nom"], "Kivu Shop")
        
    def test_historique_du_jour_avec_resume(self):
        debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur, paye=True,
                     date_livraison=debut + timedelta(seconds=1))
        creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur,
                     date_livraison=debut - timedelta(seconds=1))
        reponse = self.client_livreur.get(self.url("historique"))
        donnees = reponse.json()["data"]
        self.assertEqual(donnees["resume"], {"nb_livrees": 1, "total_usd": "4.00"})
        self.assertEqual(donnees["date"], timezone.localdate().isoformat())
        self.assertEqual(len(donnees["results"]), 1)
        self.assertTrue(donnees["results"][0]["paye"])
        self.assertNotIn("destinataire_tel", donnees["results"][0])

class TestActions(BaseTestVues):
    def test_parcours_complet(self):
        course = creer_course()
        r = self.client_livreur.post(self.url("accepter", course))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["data"]["statut"], "acceptee")
        self.assertEqual(r.json()["data"]["partenaire_nom"], "Kivu Shop")
        
        r = self.client_livreur.post(self.url("recuperer", course))
        self.assertEqual(r.json()["data"]["statut"], "recuperee")
        
        r = self.client_livreur.post(
        self.url("livrer", course), {"code": CODE_DE_CONFIRMATION}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["data"]["statut"], "livree")
        self.assertIsNotNone(r.json()["data"]["date_livraison"])
        
        r = self.client_livreur.post(self.url("payer", course))
        self.assertTrue(r.json()["data"]["paye"])
        
        h = self.client_livreur.get(self.url("historique")).json()["data"]
        self.assertEqual(h["resume"]["nb_livrees"], 1)

    def test_deuxieme_acceptation_409(self):
        course = creer_course()
        self.client_livreur.post(self.url("accepter", course))
        autre = client_authentifie(self.autre_livreur.user)
        self.verifier_erreur(
            autre.post(self.url("accepter", course)), 409, "course_non_disponible"
        )
    
    def test_course_inexistante_404(self):
        reponse = self.client_livreur.post(
            reverse("drivers:accepter", args=[999999])
        )
        self.verifier_erreur(reponse, 404, "course_introuvable")

    def test_course_d_un_autre_livreur_403(self):
        course = creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.autre_livreur)
        
        for action in ("recuperer", "livrer", "payer"):
            reponse = self.client_livreur.post(
                self.url(action, course), {"code": CODE_DE_CONFIRMATION}, format="json"
            )
            self.verifier_erreur(reponse, 403, "course_non_assignee")

    def test_livrer_une_course_non_recuperee_400(self):
        course = creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.livreur)
        reponse = self.client_livreur.post(
             self.url("livrer", course), {"code": CODE_DE_CONFIRMATION}, format="json"
        )
        self.verifier_erreur(reponse, 400, "transition_invalide")
    
    def test_code_incorrect_400(self):
        course = creer_course(statut=StatutCourse.RECUPEREE, livreur=self.livreur)
        reponse = self.client_livreur.post(
             self.url("livrer", course), {"code": "000000"}, format="json"
        )
        
        self.verifier_erreur(reponse, 400, "code_incorrect")
        self.assertIn("2 tentative", reponse.json()["error"]["detail"])
        
    def test_blocage_apres_trois_codes_faux_429(self):
        course = creer_course(statut=StatutCourse.RECUPEREE, livreur=self.livreur)
        for _ in range(3):
             self.client_livreur.post(
                  self.url("livrer", course), {"code": "000000"}, format="json"
            )
        reponse = self.client_livreur.post(
             self.url("livrer", course), {"code": CODE_DE_CONFIRMATION}, format="json"
        )
        self.verifier_erreur(reponse, 429, "livraison_bloquee")
        
    def test_code_manquant_ou_vide_400(self):
        course = creer_course(statut=StatutCourse.RECUPEREE, livreur=self.livreur)
        for corps in ({}, {"code": ""}, {"code": "   "}):
            reponse = self.client_livreur.post(
            self.url("livrer", course), corps, format="json"
        )
        self.verifier_erreur(reponse, 400, "donnees_invalides")
        
    def test_payer_course_acceptee_400(self):
        course = creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.livreur)
        reponse = self.client_livreur.post(self.url("payer", course))
        self.verifier_erreur(reponse, 400, "paiement_impossible")
        
    def test_payer_deux_fois_est_idempotent(self):
        course = creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur)
        for _ in range(2):
            reponse = self.client_livreur.post(self.url("payer", course))
            self.assertEqual(reponse.status_code, 200)
            self.assertTrue(reponse.json()["data"]["paye"])
            self.assertTrue(Course.objects.get(id=course.id).paye)
    
    def test_le_code_de_confirmation_n_est_jamais_expose(self):
        course = creer_course()
        contenus = [
            self.client_livreur.get(self.url("courses-disponibles")),
            self.client_livreur.post(self.url("accepter", course)),
            self.client_livreur.get(self.url("courses-en-cours")),
            self.client_livreur.post(self.url("recuperer", course)),
            self.client_livreur.post(
                self.url("livrer", course), {"code": "000000"}, format="json"
            ),
            self.client_livreur.post(
                self.url("livrer", course), {"code": CODE_DE_CONFIRMATION},
                format="json",
            ),
            
            self.client_livreur.get(self.url("historique")),
        ]

        for reponse in contenus:
            texte = reponse.content.decode()
            self.assertNotIn("code_confirmation", texte)
            self.assertNotIn(CODE_DE_CONFIRMATION, texte)      
