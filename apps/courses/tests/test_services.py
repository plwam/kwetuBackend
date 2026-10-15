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

class TestChangerStatut(TestCase):

    def setUp(self):
        user = User.objects.create_user(username="boutique", password="x")
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
        with patch(
            "apps.partners.services.envoyer_webhook",
            create=True,
        ) as webhook:
            webhook.delay.side_effect = Exception("panne")
            with self.captureOnCommitCallbacks(execute=True):
                course = changer_statut(self.course.id, StatutCourse.ACCEPTEE)
        self.assertEqual(course.statut, StatutCourse.ACCEPTEE)