from django.db import transaction

from .exceptions import AnnulationImpossible, TarifIntrouvable

# Statuts dans lesquels une course peut encore être annulée par le partenaire.
STATUTS_ANNULABLES = ("creee", "acceptee")


def envoyer_webhook(course_id, ancien_statut, nouveau_statut):
    """
    Programme l'envoi asynchrone du webhook après validation de la transaction.

    Appelée par ``courses.changer_statut()`` à chaque transition d'état. La
    tâche est planifiée via ``transaction.on_commit`` et n'est **jamais**
    attendue : un échec réseau ne peut pas annuler le changement de statut.
    """
    from .tasks import envoyer_webhook_task

    transaction.on_commit(
        lambda: envoyer_webhook_task.delay(course_id, ancien_statut, nouveau_statut)
    )


@transaction.atomic
def creer_course(partenaire, data):
    """
    Crée une course pour le compte du partenaire authentifié.

    Le prix est **toujours** calculé par le serveur via
    ``logistics.calculer_prix()`` ; le statut initial est fixé à ``creee`` et
    ``paye`` à ``False``. Le partenaire ne peut donc pas influencer le prix ni
    le statut.
    """
    from apps.courses.models import Course
    from apps.logistics.services import calculer_prix

    prix = calculer_prix(data["zone_depart"], data["zone_arrivee"])
    if prix is None:
        raise TarifIntrouvable()

    return Course.objects.create(
        partenaire=partenaire,
        zone_depart_id=data["zone_depart"],
        zone_arrivee_id=data["zone_arrivee"],
        destinataire_nom=data["destinataire_nom"],
        destinataire_tel=data["destinataire_tel"],
        description_colis=data.get("description_colis", ""),
        prix_usd=prix,
        statut="creee",
        paye=False,
    )


@transaction.atomic
def annuler_course(course):
    """
    Annule une course appartenant au partenaire.

    L'annulation passe obligatoirement par le point d'écriture unique de
    ``courses`` (``changer_statut``), qui valide la transition, écrit
    l'historique et déclenche le webhook. Seuls les statuts ``creee`` et
    ``acceptee`` sont annulables, sinon **409**.
    """
    from apps.courses.services import changer_statut

    if course.statut not in STATUTS_ANNULABLES:
        raise AnnulationImpossible()

    changer_statut(course.id, "annulee")
    course.refresh_from_db()
    return course
