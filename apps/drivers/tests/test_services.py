import threading
from datetime import timedelta
from decimal import Decimal
from unittest import skipUnless
from unittest.mock import patch
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from apps.courses.enums import StatutAffectation, StatutCourse
from apps.courses.exceptions import ConflitConcurrence, TransitionInvalide
from apps.courses.models import Affectation, Course, HistoriqueLivraison
from apps.drivers import services
from apps.drivers.exceptions import (
    CodeIncorrect,
    CourseIntrouvable,
    CourseNonAssignee,
    LivraisonBloquee,
    PaiementImpossible,
)
from apps.drivers.tests.outils import (
    CODE_DE_CONFIRMATION,
    creer_course,
    creer_livreur,
)

class BaseTestServices(TestCase):
    def setUp(self):
        cache.clear()
# drivers ne teste pas l'envoi HTTP du webhook : il est simulé.
        simulation = patch("apps.partners.services.envoyer_webhook")
        self.webhook_simule = simulation.start()
        self.addCleanup(simulation.stop)
        self.livreur = creer_livreur("patrick")
        self.autre_livreur = creer_livreur("esther")

class TestAccepterCourse(BaseTestServices):
    def test_acceptation_reussie(self):
        course = creer_course()
        # Le webhook est déclenché via transaction.on_commit : il faut exécuter
        # les callbacks pour observer l'appel dans un TestCase.
        with self.captureOnCommitCallbacks(execute=True):
            resultat = services.accepter_course(course.id, self.livreur)
        course.refresh_from_db()
        self.assertEqual(resultat.statut, StatutCourse.ACCEPTEE)
        self.assertEqual(course.statut, StatutCourse.ACCEPTEE)
        self.assertEqual(course.livreur_id, self.livreur.id)
        affectation = Affectation.objects.get(course=course)
        self.assertEqual(affectation.livreur_id, self.livreur.id)
        self.assertEqual(affectation.statut, StatutAffectation.ACCEPTEE)
        self.assertEqual(HistoriqueLivraison.objects.filter(course=course).count(), 1)
        self.webhook_simule.assert_called_once()

    def test_course_deja_prise_par_un_autre_livreur(self):
        course = creer_course()
        services.accepter_course(course.id, self.livreur)
        with self.assertRaises(ConflitConcurrence):
            services.accepter_course(course.id, self.autre_livreur)
    
    def test_course_annulee_non_acceptable(self):
        course = creer_course(statut=StatutCourse.ANNULEE)
        with self.assertRaises(ConflitConcurrence):
            services.accepter_course(course.id, self.livreur)
            
    def test_course_inexistante(self):
        with self.assertRaises(CourseIntrouvable):
            services.accepter_course(999999, self.livreur)

class TestMarquerRecupere(BaseTestServices):
    def test_recuperation_reussie(self):
        course = creer_course()
        services.accepter_course(course.id, self.livreur)
        resultat = services.marquer_recupere(course.id, self.livreur)
        self.assertEqual(resultat.statut, StatutCourse.RECUPEREE)
    
    def test_course_d_un_autre_livreur(self):
        course = creer_course()
        services.accepter_course(course.id, self.livreur)
        with self.assertRaises(CourseNonAssignee):
            services.marquer_recupere(course.id, self.autre_livreur)
    
    def test_mauvais_statut(self):
        course = creer_course(statut=StatutCourse.RECUPEREE, livreur=self.livreur)
        with self.assertRaises(TransitionInvalide):
            services.marquer_recupere(course.id, self.livreur)

class TestLivrerAvecCode(BaseTestServices):
    
    def creer_course_recuperee(self):
        course = creer_course()
        services.accepter_course(course.id, self.livreur)
        services.marquer_recupere(course.id, self.livreur)
        return course

    def test_livraison_reussie(self):
        course = self.creer_course_recuperee()
        resultat = services.livrer_avec_code(
            course.id, self.livreur, f"  {CODE_DE_CONFIRMATION}\n"
        )
        self.assertEqual(resultat.statut, StatutCourse.LIVREE)
        self.assertIsNotNone(resultat.date_livraison)

    def test_code_incorrect_ne_change_pas_le_statut(self):
        course = self.creer_course_recuperee()
        with self.assertRaises(CodeIncorrect):
            services.livrer_avec_code(course.id, self.livreur, "000000")
        course.refresh_from_db()
        self.assertEqual(course.statut, StatutCourse.RECUPEREE)
    
    def test_livraison_d_une_course_non_recuperee(self):
        course = creer_course()
        services.accepter_course(course.id, self.livreur)
        with self.assertRaises(TransitionInvalide):
            services.livrer_avec_code(course.id, self.livreur, CODE_DE_CONFIRMATION)
    
    def test_course_d_un_autre_livreur(self):
        course = self.creer_course_recuperee()
        with self.assertRaises(CourseNonAssignee):
            services.livrer_avec_code(
                course.id, self.autre_livreur, CODE_DE_CONFIRMATION
            )

    @override_settings(DRIVERS_MAX_TENTATIVES_CODE=3)
    def test_blocage_apres_trois_codes_faux(self):
        course = self.creer_course_recuperee()
        for _ in range(3):
            with self.assertRaises(CodeIncorrect):
                services.livrer_avec_code(course.id, self.livreur, "000000")
# même le bon code est refusé pendant le blocage
        with self.assertRaises(LivraisonBloquee):
            services.livrer_avec_code(course.id, self.livreur, CODE_DE_CONFIRMATION)
    
    @override_settings(DRIVERS_MAX_TENTATIVES_CODE=0)
    def test_limitation_desactivee(self):
        course = self.creer_course_recuperee()
        for _ in range(5):
            with self.assertRaises(CodeIncorrect):
                services.livrer_avec_code(course.id, self.livreur, "000000")
        resultat = services.livrer_avec_code(
            course.id, self.livreur, CODE_DE_CONFIRMATION
        )
        self.assertEqual(resultat.statut, StatutCourse.LIVREE)

class TestMarquerPaye(BaseTestServices):
    def test_paiement_apres_recuperation(self):
        course = creer_course(statut=StatutCourse.RECUPEREE, livreur=self.livreur)
        self.assertTrue(services.marquer_paye(course.id, self.livreur).paye)
    
    def test_paiement_apres_livraison(self):
        course = creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur)
        self.assertTrue(services.marquer_paye(course.id, self.livreur).paye)
    
    def test_paiement_idempotent(self):
        course = creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur)
        services.marquer_paye(course.id, self.livreur)
        self.assertTrue(services.marquer_paye(course.id, self.livreur).paye)

    def test_paiement_course_acceptee_refuse(self):
        course = creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.livreur)
        with self.assertRaises(PaiementImpossible):
            services.marquer_paye(course.id, self.livreur)

    def test_paiement_course_d_un_autre_livreur(self):
        course = creer_course(statut=StatutCourse.LIVREE, livreur=self.autre_livreur)
        with self.assertRaises(CourseNonAssignee):
            services.marquer_paye(course.id, self.livreur)

class TestLectures(BaseTestServices):
    def test_courses_disponibles(self):
        disponible = creer_course()
        creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.autre_livreur)
        creer_course(statut=StatutCourse.ANNULEE)
        self.assertEqual(list(services.courses_disponibles()), [disponible])

    def test_courses_en_cours_du_livreur(self):
        la_mienne = creer_course(statut=StatutCourse.ACCEPTEE, livreur=self.livreur)
        creer_course(statut=StatutCourse.RECUPEREE, livreur=self.autre_livreur)
        creer_course(statut=StatutCourse.LIVREE, livreur=self.livreur)
        self.assertEqual(
            list(services.courses_en_cours_du_livreur(self.livreur)), [la_mienne]
        )

    def test_historique_du_jour_et_resume(self):
        debut_du_jour = timezone.localtime().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        aujourdhui = creer_course(
            statut=StatutCourse.LIVREE, livreur=self.livreur,
            prix_usd=Decimal("6.00"),
            date_livraison=debut_du_jour + timedelta(seconds=1),
        )
        creer_course(  
# hier : exclue
            statut=StatutCourse.LIVREE, livreur=self.livreur,
            date_livraison=debut_du_jour - timedelta(seconds=1),
        )
        creer_course(  
# livrée par un autre livreur : exclue
            statut=StatutCourse.LIVREE, livreur=self.autre_livreur,
            date_livraison=debut_du_jour + timedelta(seconds=1),
        )
        creer_course(statut=StatutCourse.RECUPEREE, livreur=self.livreur)  # exclue
        self.assertEqual(list(services.historique_du_jour(self.livreur)), [aujourdhui])
        self.assertEqual(
            services.resume_du_jour(self.livreur),
            {"nb_livrees": 1, "total_usd": "6.00"},
        )
    def test_resume_du_jour_sans_livraison(self):
        self.assertEqual(
            services.resume_du_jour(self.livreur),
            {"nb_livrees": 0, "total_usd": "0.00"},
        )

@skipUnless(
    connection.vendor == "postgresql",
    "select_for_update() est ignoré par SQLite : test à exécuter sur PostgreSQL.",
)

class TestAcceptationConcurrente(TransactionTestCase):
    def test_un_seul_livreur_obtient_la_course(self):
        livreurs = [creer_livreur(f"livreur{i}") for i in range(2)]
        course = creer_course()
        resultats = []
        def tenter(livreur):
            try:
                services.accepter_course(course.id, livreur)
                resultats.append("ok")
            except ConflitConcurrence:
                resultats.append("conflit")
            finally:
                connection.close()
        with patch("apps.partners.services.envoyer_webhook.delay"):
            fils = [threading.Thread(target=tenter, args=(l,)) for l in livreurs]
            for fil in fils:
                fil.start()
            for fil in fils:
                fil.join()
        self.assertEqual(sorted(resultats), ["conflit", "ok"])
        self.assertEqual(Affectation.objects.filter(course=course).count(), 1)
            