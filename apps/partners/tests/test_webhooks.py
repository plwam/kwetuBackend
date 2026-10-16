"""Contrat du webhook sortant exposé par ``partners`` à ``courses``.

Le document de conception (§2.3 et §4.1) impose que ``courses.changer_statut()``
appelle ``partners.services.envoyer_webhook`` **toujours** via ``.delay()``,
après validation de la transaction. ``envoyer_webhook`` est donc la tâche
Celery elle-même.
"""

from unittest.mock import patch

import pytest
from django.db import transaction

from apps.courses.services import changer_statut
from apps.partners.services import envoyer_webhook
from apps.partners.tasks import envoyer_webhook_task

pytestmark = pytest.mark.django_db


class TestContratEnvoyerWebhook:
    def test_expose_la_tache_celery_attendue_par_courses(self):
        assert envoyer_webhook is envoyer_webhook_task
        assert hasattr(envoyer_webhook, "delay")


class TestProgrammationParCourses:
    def test_le_webhook_est_planifie_apres_commit(
        self, partenaire, creer_course_factory, django_capture_on_commit_callbacks
    ):
        course = creer_course_factory(partenaire, statut="creee")

        with patch("apps.partners.tasks.envoyer_webhook_task.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=True):
                changer_statut(course.id, "acceptee")

        mock_delay.assert_called_once_with(course.id, "creee", "acceptee")

    def test_aucun_webhook_si_la_transaction_echoue(
        self, partenaire, creer_course_factory, django_capture_on_commit_callbacks
    ):
        course = creer_course_factory(partenaire, statut="creee")

        with patch("apps.partners.tasks.envoyer_webhook_task.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=False):
                with pytest.raises(RuntimeError):
                    with transaction.atomic():
                        changer_statut(course.id, "acceptee")
                        raise RuntimeError("rollback simulé")

        assert mock_delay.call_count == 0
        course.refresh_from_db()
        assert course.statut == "creee"
