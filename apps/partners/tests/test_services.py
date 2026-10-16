from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.partners.exceptions import AnnulationImpossible, TarifIntrouvable
from apps.partners.services import annuler_course, creer_course

pytestmark = pytest.mark.django_db

DONNEES_COURSE = {
    "destinataire_nom": "Amani K.",
    "destinataire_tel": "+243970000000",
    "description_colis": "Robe en carton",
}


class TestCreerCourse:
    @patch("apps.logistics.services.calculer_prix", return_value=Decimal("7.50"))
    def test_le_prix_est_calcule_par_le_serveur(
        self, mock_prix, partenaire, zone_model, course_model
    ):
        zone_depart = zone_model.objects.create(nom="Goma")
        zone_arrivee = zone_model.objects.create(nom="Kinshasa")

        course = creer_course(
            partenaire,
            {
                "zone_depart": zone_depart.id,
                "zone_arrivee": zone_arrivee.id,
                **DONNEES_COURSE,
            },
        )

        assert course.partenaire == partenaire
        assert str(course.prix_usd) == "7.50"
        assert course.statut == "creee"
        assert course.paye is False

    @patch("apps.logistics.services.calculer_prix", return_value=None)
    def test_aucun_tarif_leve_une_erreur(self, mock_prix, partenaire, zone_model):
        zone_depart = zone_model.objects.create(nom="Goma")
        zone_arrivee = zone_model.objects.create(nom="Kinshasa")

        with pytest.raises(TarifIntrouvable):
            creer_course(
                partenaire,
                {
                    "zone_depart": zone_depart.id,
                    "zone_arrivee": zone_arrivee.id,
                    **DONNEES_COURSE,
                },
            )


class TestAnnulerCourse:
    def test_annulation_d_une_course_creee(self, partenaire, creer_course_factory):
        course = creer_course_factory(partenaire, statut="creee")

        resultat = annuler_course(course)

        assert resultat.statut == "annulee"

    def test_annulation_refusee_si_course_livree(
        self, partenaire, creer_course_factory
    ):
        course = creer_course_factory(partenaire, statut="livree")

        with pytest.raises(AnnulationImpossible):
            annuler_course(course)
