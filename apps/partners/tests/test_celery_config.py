"""Tests de l'activation de Celery pour le pipeline de webhooks.

Ces tests échouent si ``config/__init__.py`` (qui importe ``config/celery.py``)
est absent : sans lui, ``shared_task`` se rattache à l'app Celery par défaut,
le broker des réglages est ignoré et les webhooks ne sont jamais publiés.
"""

from unittest.mock import Mock, patch

import pytest
from celery import current_app
from django.conf import settings

from apps.partners.models import WebhookLog
from apps.partners.services import envoyer_webhook

pytestmark = pytest.mark.django_db


class TestApplicationCelery:
    def test_l_application_celery_du_projet_est_chargee(self):
        assert current_app.main == "mashop_delivery"

    def test_le_broker_est_celui_des_reglages(self):
        assert current_app.conf.broker_url == settings.CELERY_BROKER_URL

    @patch("apps.partners.tasks.requests.post")
    def test_le_webhook_part_en_mode_eager(
        self, mock_post, partenaire, creer_course_factory
    ):
        """Scénario 16 du doc : réponse 200 du partenaire → ``WebhookLog`` succès."""
        if not current_app.conf.task_always_eager:
            pytest.skip("Le mode eager n'est pas actif dans ces réglages.")

        mock_post.return_value = Mock(status_code=200, ok=True)
        course = creer_course_factory(partenaire)

        envoyer_webhook.delay(course.id, "creee", "acceptee")

        log = WebhookLog.objects.get()
        assert log.succes is True
        assert log.statut_http == 200
        mock_post.assert_called_once()
