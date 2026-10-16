import pytest

from apps.partners.models import WebhookLog

pytestmark = pytest.mark.django_db


class TestWebhookLog:
    def test_creation_et_representation(self, partenaire, creer_course_factory):
        course = creer_course_factory(partenaire)

        log = WebhookLog.objects.create(
            course=course,
            url="https://kivushop.cd/webhook",
            payload={"reference": course.reference, "nouveau_statut": "acceptee"},
            statut_http=200,
            succes=True,
        )

        assert log.succes is True
        assert log.statut_http == 200
        assert str(log).startswith(f"Webhook course #{course.id}")
        assert "OK" in str(log)

    def test_une_ligne_par_tentative(self, partenaire, creer_course_factory):
        course = creer_course_factory(partenaire)

        for _ in range(3):
            WebhookLog.objects.create(
                course=course,
                url="https://kivushop.cd/webhook",
                payload={"reference": course.reference},
                statut_http=None,
                succes=False,
            )

        assert WebhookLog.objects.filter(course=course).count() == 3

    def test_suppression_en_cascade_avec_la_course(
        self, partenaire, creer_course_factory
    ):
        course = creer_course_factory(partenaire)
        WebhookLog.objects.create(
            course=course,
            url="https://kivushop.cd/webhook",
            payload={"reference": course.reference},
            statut_http=200,
            succes=True,
        )

        course.delete()

        assert WebhookLog.objects.count() == 0
