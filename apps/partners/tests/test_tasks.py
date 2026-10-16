from unittest.mock import Mock, patch

import pytest
import requests
from celery.exceptions import Retry

from apps.partners.models import WebhookLog
from apps.partners.tasks import envoyer_webhook_task

pytestmark = pytest.mark.django_db

# On appelle ``envoyer_webhook_task.run(...)`` plutôt que ``.apply(...)`` : le
# corps de la tâche est ainsi exécuté de façon **déterministe**, que Celery soit
# configuré ou non, et en mode « eager » ou non. Un échec réseau doit demander
# une relance, ce que Celery signale en levant ``Retry``.


class TestEnvoyerWebhookTask:
    @patch("apps.partners.tasks.requests.post")
    def test_envoi_reussi_journalise(self, mock_post, partenaire, creer_course_factory):
        mock_post.return_value = Mock(status_code=200, ok=True)
        course = creer_course_factory(partenaire)

        envoyer_webhook_task.run(course.id, "creee", "acceptee")

        log = WebhookLog.objects.get()
        assert log.succes is True
        assert log.statut_http == 200
        assert log.url == partenaire.url_webhook
        assert log.payload["reference"] == course.reference

    @patch("apps.partners.tasks.requests.post")
    def test_echec_reseau_journalise(self, mock_post, partenaire, creer_course_factory):
        mock_post.side_effect = requests.ConnectionError("partenaire injoignable")
        course = creer_course_factory(partenaire)

        # Un échec réseau programme une relance. Appelée directement (hors
        # worker), Celery ré-exécute l'exception d'origine ; via un worker/eager
        # il lève ``Retry``. On accepte les deux, sans dépendre de la config.
        with pytest.raises((Retry, requests.ConnectionError)):
            envoyer_webhook_task.run(course.id, "creee", "acceptee")

        # Une ligne est journalisée par tentative (1 essai + les relances).
        logs = WebhookLog.objects.filter(succes=False)
        assert logs.count() >= 1
        assert all(log.statut_http is None for log in logs)
        # Le statut de la course n'est jamais modifié par un échec de webhook.
        course.refresh_from_db()
        assert course.statut == "creee"

    @patch("apps.partners.tasks.requests.post")
    def test_partenaire_sans_url_aucun_envoi(
        self, mock_post, partenaire_sans_webhook, creer_course_factory
    ):
        course = creer_course_factory(partenaire_sans_webhook)

        envoyer_webhook_task.run(course.id, "creee", "acceptee")

        mock_post.assert_not_called()
        assert WebhookLog.objects.count() == 0
