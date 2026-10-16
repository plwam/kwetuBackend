from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import Partenaire, User
from apps.courses.models import Course
from apps.logistics.exceptions import TarifIntrouvable
from apps.logistics.models import Tarif, Zone
from apps.logistics.services import (
    calculer_prix,
    creer_zone,
    modifier_tarif,
    zone_est_utilisee,
)


class CalculerPrixTest(TestCase):
    """Tests du service calculer_prix()."""

    def setUp(self):
        """Préparation : créer zones et tarifs."""
        self.zone_a = Zone.objects.create(nom="Himbi")
        self.zone_b = Zone.objects.create(nom="Birene")
        self.zone_c = Zone.objects.create(nom="Katindo")

    def test_calculer_prix_valide(self):
        """Retourne le prix correct pour un trajet valide."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        prix = calculer_prix(self.zone_a.id, self.zone_b.id)
        self.assertEqual(prix, Decimal("4.00"))

    def test_calculer_prix_tarif_introuvable(self):
        """Lève TarifIntrouvable si aucun tarif n'existe."""
        with self.assertRaises(TarifIntrouvable):
            calculer_prix(self.zone_a.id, self.zone_b.id)

    def test_calculer_prix_ignore_tarif_inactif(self):
        """Un tarif inactif est ignoré."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
            actif=False,
        )
        with self.assertRaises(TarifIntrouvable):
            calculer_prix(self.zone_a.id, self.zone_b.id)

    def test_calculer_prix_ne_confond_pas_les_sens(self):
        """Himbi→Birene n'est pas équivalent à Birene→Himbi."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        # Birene→Himbi n'existe pas
        with self.assertRaises(TarifIntrouvable):
            calculer_prix(self.zone_b.id, self.zone_a.id)

    def test_calculer_prix_deux_sens(self):
        """Les deux sens ont des prix différents."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        Tarif.objects.create(
            zone_depart=self.zone_b,
            zone_arrivee=self.zone_a,
            prix_usd=Decimal("6.00"),
        )
        prix_aller = calculer_prix(self.zone_a.id, self.zone_b.id)
        prix_retour = calculer_prix(self.zone_b.id, self.zone_a.id)
        self.assertEqual(prix_aller, Decimal("4.00"))
        self.assertEqual(prix_retour, Decimal("6.00"))

    def test_calculer_prix_zones_identiques(self):
        """Un trajet Himbi→Himbi peut avoir un tarif."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_a,
            prix_usd=Decimal("2.00"),
        )
        prix = calculer_prix(self.zone_a.id, self.zone_a.id)
        self.assertEqual(prix, Decimal("2.00"))

    def test_calculer_prix_zone_inexistante(self):
        """Une zone inexistante lève TarifIntrouvable."""
        with self.assertRaises(TarifIntrouvable):
            calculer_prix(999, 1000)

    def test_calculer_prix_plusieurs_tarifs(self):
        """Plusieurs tarifs disponibles, on récupère le bon."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_c,
            prix_usd=Decimal("6.00"),
        )
        self.assertEqual(
            calculer_prix(self.zone_a.id, self.zone_b.id),
            Decimal("4.00"),
        )
        self.assertEqual(
            calculer_prix(self.zone_a.id, self.zone_c.id),
            Decimal("6.00"),
        )

    def test_calculer_prix_ne_modifie_rien(self):
        """calculer_prix ne crée, ni ne modifie, ni ne supprime rien."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        tarifs_avant = Tarif.objects.count()
        calculer_prix(self.zone_a.id, self.zone_b.id)
        self.assertEqual(Tarif.objects.count(), tarifs_avant)


class ZoneEstUtiliseeTest(TestCase):
    """Tests du service zone_est_utilisee()."""

    def setUp(self):
        """Préparation : créer zones et un partenaire."""
        self.zone_a = Zone.objects.create(nom="Himbi")
        self.zone_b = Zone.objects.create(nom="Birene")
        self.zone_c = Zone.objects.create(nom="Katindo")
        utilisateur = User.objects.create_user(
            email="partenaire@test.com",
            nom="Kivu",
            prenom="Shop",
            telephone="+243900000000",
            role="PARTENAIRE",
        )
        self.partenaire = Partenaire.objects.create(
            user=utilisateur, nom_boutique="Kivu Shop"
        )

    def _creer_course(self, zone_depart, zone_arrivee):
        """Crée une course avec tous les champs obligatoires."""
        return Course.objects.create(
            partenaire=self.partenaire,
            zone_depart=zone_depart,
            zone_arrivee=zone_arrivee,
            destinataire_nom="Client",
            destinataire_tel="+243970000001",
            description_colis="Colis",
            prix_usd=Decimal("4.00"),
        )

    def test_zone_non_utilisee(self):
        """Sans course, la zone n'est pas utilisée."""
        self.assertFalse(zone_est_utilisee(self.zone_a.id))

    def test_zone_utilisee_en_depart(self):
        """Une zone utilisée en départ est utilisée."""
        self._creer_course(self.zone_a, self.zone_b)
        self.assertTrue(zone_est_utilisee(self.zone_a.id))

    def test_zone_utilisee_en_arrivee(self):
        """Une zone utilisée en arrivée est utilisée."""
        self._creer_course(self.zone_b, self.zone_a)
        self.assertTrue(zone_est_utilisee(self.zone_a.id))

    def test_zone_non_utilisee_parmi_dautres(self):
        """Une zone non utilisée n'est pas marquée utilisée."""
        self._creer_course(self.zone_a, self.zone_b)
        self.assertFalse(zone_est_utilisee(self.zone_c.id))


class CreerZoneTest(TestCase):
    """Tests du service creer_zone()."""

    def test_creer_zone_valide(self):
        """Crée une zone avec le statut ACTIVE."""
        zone = creer_zone(nom="Himbi", description="Quartier Himbi")
        self.assertEqual(zone.nom, "Himbi")
        self.assertEqual(zone.statut, "ACTIVE")

    def test_creer_zone_sans_description(self):
        """La description est optionnelle."""
        zone = creer_zone(nom="Himbi")
        self.assertEqual(zone.description, "")


class ModifierTarifTest(TestCase):
    """Tests du service modifier_tarif()."""

    def setUp(self):
        """Préparation : créer zones et un tarif."""
        self.zone_a = Zone.objects.create(nom="Himbi")
        self.zone_b = Zone.objects.create(nom="Birene")
        self.tarif = Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )

    def test_modifier_prix(self):
        """Modifie le prix d'un tarif."""
        modifier_tarif(self.tarif, prix_usd=Decimal("5.00"))
        self.tarif.refresh_from_db()
        self.assertEqual(self.tarif.prix_usd, Decimal("5.00"))

    def test_modifier_actif(self):
        """Modifie l'état actif d'un tarif."""
        modifier_tarif(self.tarif, actif=False)
        self.tarif.refresh_from_db()
        self.assertFalse(self.tarif.actif)

    def test_modifier_les_deux(self):
        """Modifie prix et actif en même temps."""
        modifier_tarif(self.tarif, prix_usd=Decimal("6.00"), actif=False)
        self.tarif.refresh_from_db()
        self.assertEqual(self.tarif.prix_usd, Decimal("6.00"))
        self.assertFalse(self.tarif.actif)