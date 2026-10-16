from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import Livreur, Partenaire, User
from apps.courses.enums import StatutCourse
from apps.courses.exceptions import TransitionInvalide
from apps.courses.models import Course, HistoriqueLivraison
from apps.courses.services import changer_statut
from apps.logistics.models import Zone

from apps.courses.exceptions import (
    AffectationInvalide,
    CourseDejaAffectee,
    LivreurNonEligible,
    TransitionInvalide,
)
from apps.courses.models import Affectation, Course, HistoriqueLivraison
from apps.courses.services import assigner_course, changer_statut, zone_est_utilisee

from apps.accounts.models import Livreur, Partenaire, User

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



class TestChangerStatut(TestCase):

    def setUp(self):
        user = creer_utilisateur(email="boutique@example.com")

        self.partenaire = Partenaire.objects.create(user=user, nom_boutique="Boutique")
        self.zone_a = Zone.objects.create(nom="Zone A")
        self.zone_b = Zone.objects.create(nom="Zone B")
        self.course = Course.objects.create(
            reference="GM-0001",
            partenaire=self.partenaire,
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            destinataire_nom="Client Test",
            destinataire_tel="000000",
            description_colis="Colis test",
            prix_usd=Decimal("5.00"),
        )

    def test_transition_valide_change_le_statut(self):
        course = changer_statut(self.course.id, StatutCourse.ACCEPTEE)
        self.assertEqual(course.statut, StatutCourse.ACCEPTEE)

    def test_transition_valide_cree_un_historique(self):
        changer_statut(self.course.id, StatutCourse.ACCEPTEE, commentaire="ok")
        self.assertEqual(HistoriqueLivraison.objects.count(), 1)
        ligne = HistoriqueLivraison.objects.get()
        self.assertEqual(ligne.ancien_statut, StatutCourse.CREEE)
        self.assertEqual(ligne.nouveau_statut, StatutCourse.ACCEPTEE)
        self.assertEqual(ligne.commentaire, "ok")

    def test_transition_interdite_leve_une_exception(self):
        with self.assertRaises(TransitionInvalide):
            changer_statut(self.course.id, StatutCourse.LIVREE)
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut, StatutCourse.CREEE)
        self.assertEqual(HistoriqueLivraison.objects.count(), 0)

    def test_statut_inconnu_est_refuse(self):
        with self.assertRaises(TransitionInvalide):
            changer_statut(self.course.id, "n_importe_quoi")

    def test_course_inexistante(self):
        with self.assertRaises(Course.DoesNotExist):
            changer_statut(99999, StatutCourse.ACCEPTEE)

    def test_livraison_renseigne_la_date(self):
        changer_statut(self.course.id, StatutCourse.ACCEPTEE)
        changer_statut(self.course.id, StatutCourse.RECUPEREE)
        course = changer_statut(self.course.id, StatutCourse.LIVREE)
        self.assertIsNotNone(course.date_livraison)

    def test_webhook_declenche_apres_commit(self):
        with patch("apps.courses.services._notifier_partenaire") as notifier:
            with self.captureOnCommitCallbacks(execute=True):
                changer_statut(self.course.id, StatutCourse.ACCEPTEE)
        notifier.assert_called_once_with(
            self.course.id, StatutCourse.CREEE, StatutCourse.ACCEPTEE
        )

    def test_echec_webhook_ne_bloque_pas_le_statut(self):
        with patch("apps.partners.services.envoyer_webhook.delay") as mock_delay:
            mock_delay.side_effect = Exception("panne")
            with self.captureOnCommitCallbacks(execute=True):
                course = changer_statut(self.course.id, StatutCourse.ACCEPTEE)
        self.assertEqual(course.statut, StatutCourse.ACCEPTEE)

    def test_webhook_appele_avec_les_bons_arguments(self):
        with patch("apps.partners.services.envoyer_webhook.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                changer_statut(self.course.id, StatutCourse.ACCEPTEE)
        mock_delay.assert_called_once_with(
            self.course.id, StatutCourse.CREEE, StatutCourse.ACCEPTEE
        )

class TestReferenceCourse(TestCase):

    def setUp(self):
        user = creer_utilisateur(email="boutique@example.com")
        self.partenaire = Partenaire.objects.create(user=user, nom_boutique="Boutique")
        self.zone_a = Zone.objects.create(nom="Zone A")
        self.zone_b = Zone.objects.create(nom="Zone B")

    def _creer_course(self):
        return Course.objects.create(
            partenaire=self.partenaire,
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            destinataire_nom="Client",
            destinataire_tel="000",
            description_colis="Colis",
            prix_usd=Decimal("5.00"),
        )

    def test_reference_generee_automatiquement(self):
        course = self._creer_course()
        self.assertEqual(course.reference, f"GM-{course.pk:04d}")
        self.assertFalse(course.reference.startswith("TMP-"))

    def test_references_uniques(self):
        c1 = self._creer_course()
        c2 = self._creer_course()
        self.assertNotEqual(c1.reference, c2.reference)

    def test_reference_inchangee_a_la_modification(self):
        course = self._creer_course()
        ancienne = course.reference
        course.paye = True
        course.save()
        course.refresh_from_db()
        self.assertEqual(course.reference, ancienne)

    def test_code_confirmation_genere(self):
        course = self._creer_course()
        self.assertEqual(len(course.code_confirmation), 6)
        self.assertTrue(course.code_confirmation.isdigit())

    def test_code_inchange_a_la_modification(self):
        course = self._creer_course()
        ancien = course.code_confirmation
        course.paye = True
        course.save()
        course.refresh_from_db()
        self.assertEqual(course.code_confirmation, ancien)

    def test_verifier_code_correct(self):
        course = self._creer_course()
        self.assertTrue(course.verifier_code(course.code_confirmation))

    def test_verifier_code_incorrect(self):
        course = self._creer_course()
        faux = "000000" if course.code_confirmation != "000000" else "111111"
        self.assertFalse(course.verifier_code(faux))

    def test_verifier_code_vide(self):
        course = self._creer_course()
        self.assertFalse(course.verifier_code(""))
        self.assertFalse(course.verifier_code(None))