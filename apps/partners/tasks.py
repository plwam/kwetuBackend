import requests
from celery import shared_task
from django.apps import apps


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def envoyer_webhook_task(self, course_id, ancien_statut, nouveau_statut):
    Course = apps.get_model("courses", "Course")
    WebhookLog = apps.get_model("partners", "WebhookLog")

    try:
        course = Course.objects.select_related("partenaire").get(id=course_id)
    except Course.DoesNotExist:
        return

    url_webhook = getattr(course.partenaire, "url_webhook", None)
    if not url_webhook:
        return  # Pas d'URL configurée, on ne fait rien

    payload = {
        "reference": course.reference,
        "ancien_statut": ancien_statut,
        "nouveau_statut": nouveau_statut,
    }

    statut_http = None
    succes = False

    try:
        response = requests.post(url_webhook, json=payload, timeout=5)
        statut_http = response.status_code
        succes = response.ok

        WebhookLog.objects.create(
            course=course,
            url=url_webhook,
            payload=payload,
            statut_http=statut_http,
            succes=succes,
        )

        if not succes and statut_http >= 500:
            raise requests.RequestException(
                f"Erreur serveur partenaire HTTP {statut_http}"
            )

    except requests.RequestException as exc:
        WebhookLog.objects.create(
            course=course,
            url=url_webhook,
            payload=payload,
            statut_http=statut_http,
            succes=False,
        )
        raise self.retry(exc=exc)
