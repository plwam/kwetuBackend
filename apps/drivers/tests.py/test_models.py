from django.apps import apps
from django.test import TestCase

class TestAbsenceDeModeles(TestCase):
    """drivers ne possède aucun modèle : ce test empêche d'en ajouter par erreur."""
    
    def test_drivers_ne_possede_aucun_modele(self):
        modeles = list(apps.get_app_config("drivers").get_models())
        self.assertEqual(modeles, [])