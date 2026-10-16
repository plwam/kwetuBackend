from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.logistics.models import StatutZone, Tarif, Zone


class ZoneViewSetTest(TestCase):
    """Tests des endpoints admin sur les zones."""

    def setUp(self):
        """Préparation : créer un admin et un client API."""
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            nom="Admin",
            prenom="Test",
            telephone="+243970000010",
            password="password123",
            role="ADMIN",
        )
        self.client.force_authenticate(user=self.admin)

    def test_lister_zones(self):
        """GET /admin/zones/ retourne la liste."""
        Zone.objects.create(nom="Himbi")
        Zone.objects.create(nom="Birene")

        response = self.client.get("/api/v1/logistics/admin/zones/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_creer_zone(self):
        """POST /admin/zones/ crée une zone."""
        response = self.client.post(
            "/api/v1/logistics/admin/zones/",
            {"nom": "Himbi", "description": "Quartier Himbi"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["nom"], "Himbi")

    def test_creer_zone_doublon(self):
        """POST avec nom dupliqué → 400."""
        Zone.objects.create(nom="Himbi")
        response = self.client.post(
            "/api/v1/logistics/admin/zones/",
            {"nom": "Himbi"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "zone_existe")

    def test_supprimer_zone_non_utilisee(self):
        """DELETE sur une zone non utilisée → 204."""
        zone = Zone.objects.create(nom="Himbi")
        response = self.client.delete(
            f"/api/v1/logistics/admin/zones/{zone.id}/"
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Zone.objects.filter(id=zone.id).exists())

    def test_acces_refuse_sans_auth(self):
        """Sans authentification → 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/logistics/admin/zones/")
        self.assertEqual(response.status_code, 401)

    def test_acces_refuse_partenaire(self):
        """Un partenaire ne peut pas accéder à l'admin → 403."""
        partenaire = User.objects.create_user(
            email="partenaire@test.com",
            nom="Partenaire",
            prenom="Test",
            telephone="+243970000011",
            password="password123",
            role="PARTENAIRE",
        )
        self.client.force_authenticate(user=partenaire)
        response = self.client.get("/api/v1/logistics/admin/zones/")
        self.assertEqual(response.status_code, 403)


class TarifViewSetTest(TestCase):
    """Tests des endpoints admin sur les tarifs."""

    def setUp(self):
        """Préparation : créer un admin, deux zones."""
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            nom="Admin",
            prenom="Test",
            telephone="+243970000010",
            password="password123",
            role="ADMIN",
        )
        self.client.force_authenticate(user=self.admin)

        self.zone_a = Zone.objects.create(nom="Himbi")
        self.zone_b = Zone.objects.create(nom="Birene")

    def test_creer_tarif(self):
        """POST /admin/tarifs/ crée un tarif."""
        response = self.client.post(
            "/api/v1/logistics/admin/tarifs/",
            {
                "zone_depart": self.zone_a.id,
                "zone_arrivee": self.zone_b.id,
                "prix_usd": "4.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["prix_usd"], "4.00")

    def test_creer_tarif_prix_invalide(self):
        """POST avec prix négatif → 400."""
        response = self.client.post(
            "/api/v1/logistics/admin/tarifs/",
            {
                "zone_depart": self.zone_a.id,
                "zone_arrivee": self.zone_b.id,
                "prix_usd": "-5.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_creer_tarif_doublon(self):
        """POST avec couple dupliqué → 400."""
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )
        response = self.client.post(
            "/api/v1/logistics/admin/tarifs/",
            {
                "zone_depart": self.zone_a.id,
                "zone_arrivee": self.zone_b.id,
                "prix_usd": "5.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class DevisViewTest(TestCase):
    """Tests de l'endpoint devis (partenaire)."""

    def setUp(self):
        """Préparation : créer zones et tarif."""
        self.client = APIClient()
        self.zone_a = Zone.objects.create(nom="Himbi")
        self.zone_b = Zone.objects.create(nom="Birene")
        Tarif.objects.create(
            zone_depart=self.zone_a,
            zone_arrivee=self.zone_b,
            prix_usd=Decimal("4.00"),
        )

    def test_devis_sans_auth(self):
        """Sans clé API → 401."""
        response = self.client.post(
            "/api/v1/logistics/partenaire/devis/",
            {"zone_depart": self.zone_a.id, "zone_arrivee": self.zone_b.id},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_devis_zones_invalides(self):
        """Payload invalide → 400."""
        # À tester une fois l'authentification partenaire prête
        pass