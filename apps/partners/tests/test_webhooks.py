from unittest.mock import patch

import pytest
from django.db import transaction

from apps.partners.services import envoyer_webhook

pytestmark = pytest.mark.django_db


class TestProgrammationDuWebhook:
    def test_le_webhook_est_planifie_apres_commit(
        self, django_capture_on_commit_callbacks
    ):
        with patch("apps.partners.tasks.envoyer_webhook_task.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=True):
                envoyer_webhook(42, "creee", "acceptee")

        mock_delay.assert_called_once_with(42, "creee", "acceptee")

    def test_aucun_webhook_si_la_transaction_echoue(
        self, django_capture_on_commit_callbacks
    ):
        with patch("apps.partners.tasks.envoyer_webhook_task.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=False):
                with pytest.raises(RuntimeError):
                    with transaction.atomic():
                        envoyer_webhook(42, "creee", "acceptee")
                        raise RuntimeError("rollback simulé")

        assert mock_delay.call_count == 0
