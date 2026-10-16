from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.logistics.models import StatutZone, Tarif, Zone


class ZoneModelTest(TestCase):
    """Tests du modèle Zone."""

    def test_creation_zone_valide(self):
        """Créer une zone avec des données valides."""
        zone = Zone.objects.create(
            nom="Himbi",
            description="Quartier Himbi",
        )
        self.assertEqual(zone.nom, "Himbi")
        self.assertEqual(zone.statut, StatutZone.ACTIVE)
        self.assertEqual(zone.description, "Quartier Himbi")

    def test_zone_nom_unique(self):
        """Créer deux zones avec le même nom doit échouer."""
        Zone.objects.create(nom="Himbi")
        with self.assertRaises(IntegrityError):
            Zone.objects.create(nom="Himbi")

    def test_zone_str(self):
        """La représentation d'une zone est son nom."""
        zone = Zone.objects.create(nom="Himbi")
        self.assertEqual(str(zone), "Himbi")

    def test_zone_statut_par_defaut(self):
        """Le statut par défaut est ACTIVE."""
        zone = Zone.objects.create(nom="Himbi")
        self.assertEqual(zone.statut, "ACTIVE")

    def test_zone_statut_inactif(self):
        """On peut créer une zone avec le statut INACTIVE."""
        zone = Zone.objects.create(nom="Himbi", statut=StatutZone.INACTIVE)
        self.assertEqual(zone.statut, "INACTIVE")

    def test_zone_description_optionnelle(self):
        """La description est optionnelle."""
        zone = Zone.objects.create(nom="Himbi")
        self.assertEqual(zone.description, "")


class TarifModelTest(TestCase):
    """Tests du modèle Tarif."""

    def setUp(self):
        """Préparation : créer deux zones pour les tests."""
        self.zone_a = Zone.objects.create(nom="Himbi")
        self.zone_b = Zone.objects.create(nom="Birene")

    def test_creation_tarif_valide(self):
        """Créer un tarif avec des données valides."""
        tarif = Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        self.assertEqual(tarif.zone_depart, self.zone_a)
        self.assertEqual(tarif.zone_arrivee, self.zone_b)
        self.assertEqual(tarif.prix_usd, Decimal("4.00"))
        self.assertTrue(tarif.actif)

    def test_tarif_prix_positif(self):
        """Le prix doit être strictement supérieur à 0."""
        tarif = Tarif(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            tarif.full_clean()

    def test_tarif_prix_negatif(self):
        """Un prix négatif est refusé."""
        tarif = Tarif(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("-5.00"),
        )
        with self.assertRaises(ValidationError):
            tarif.full_clean()

    def test_tarif_couple_unique(self):
        """Deux tarifs pour le même couple doivent échouer."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        with self.assertRaises(IntegrityError):
            Tarif.objects.create(
                zone_depart=self.zone_a,
                zone_arrivee=self.zone_b,
                prix_usd=Decimal("5.00"),
            )

    def test_tarif_sens_inverse_autorise(self):
        """Himbi→Birene et Birene→Himbi sont deux tarifs distincts."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        tarif_inverse = Tarif.objects.create(
            zone_depart=self.zone_b,
            zone_arrivee=self.zone_a,
            prix_usd=Decimal("6.00"),
        )
        self.assertEqual(tarif_inverse.prix_usd, Decimal("6.00"))

    def test_tarif_str(self):
        """La représentation d'un tarif contient les noms et le prix."""
        tarif = Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        self.assertIn("Himbi", str(tarif))
        self.assertIn("Birene", str(tarif))
        self.assertIn("4.00", str(tarif))

    def test_tarif_actif_par_defaut(self):
        """Un tarif est actif par défaut."""
        tarif = Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        self.assertTrue(tarif.actif)