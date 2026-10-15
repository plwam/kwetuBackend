from django.test import SimpleTestCase

from apps.courses.enums import StatutCourse
from apps.courses.state_machine import (
    TRANSITIONS_AUTORISEES,
    transition_est_autorisee,
)


class TestMachineAEtats(SimpleTestCase):

    def test_transitions_autorisees(self):
        autorisees = [
            (StatutCourse.CREEE, StatutCourse.ACCEPTEE),
            (StatutCourse.CREEE, StatutCourse.ANNULEE),
            (StatutCourse.ACCEPTEE, StatutCourse.RECUPEREE),
            (StatutCourse.ACCEPTEE, StatutCourse.ANNULEE),
            (StatutCourse.RECUPEREE, StatutCourse.LIVREE),
        ]
        for ancien, nouveau in autorisees:
            with self.subTest(ancien=ancien, nouveau=nouveau):
                self.assertTrue(transition_est_autorisee(ancien, nouveau))

    def test_toutes_les_autres_transitions_sont_interdites(self):
        autorisees = {
            (ancien, nouveau)
            for ancien, cibles in TRANSITIONS_AUTORISEES.items()
            for nouveau in cibles
        }
        for ancien in StatutCourse:
            for nouveau in StatutCourse:
                if (ancien, nouveau) in autorisees:
                    continue
                with self.subTest(ancien=ancien, nouveau=nouveau):
                    self.assertFalse(transition_est_autorisee(ancien, nouveau))

    def test_statuts_finaux_sans_sortie(self):
        self.assertEqual(TRANSITIONS_AUTORISEES[StatutCourse.LIVREE], [])
        self.assertEqual(TRANSITIONS_AUTORISEES[StatutCourse.ANNULEE], [])

    def test_creee_ne_peut_pas_aller_directement_a_livree(self):
        self.assertFalse(
            transition_est_autorisee(StatutCourse.CREEE, StatutCourse.LIVREE)
        )

    def test_statut_inconnu_est_refuse(self):
        self.assertFalse(transition_est_autorisee("n_importe_quoi", StatutCourse.ACCEPTEE))