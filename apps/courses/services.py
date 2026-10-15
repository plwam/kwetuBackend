import logging

from django.db import transaction
from django.utils import timezone

from apps.courses.enums import StatutCourse
from apps.courses.exceptions import TransitionInvalide
from apps.courses.models import Course, HistoriqueLivraison
from apps.courses.state_machine import transition_est_autorisee

from apps.courses.exceptions import (
    AffectationInvalide,
    CourseDejaAffectee,
    LivreurNonEligible,
    TransitionInvalide,
)
from apps.courses.models import Affectation, Course, HistoriqueLivraison
from apps.courses.enums import StatutAffectation, StatutCourse

from django.db.models import Q

logger = logging.getLogger(__name__)


def _notifier_partenaire(course_id, ancien_statut, nouveau_statut):
    """Déclenche le webhook. Une erreur ici ne doit jamais casser le changement de statut."""
    try:
        # Import local : évite l'import circulaire et l'erreur tant que partners n'existe pas.
        from apps.partners.services import envoyer_webhook

        envoyer_webhook.delay(course_id, ancien_statut, nouveau_statut)
    except Exception:
        logger.exception("Échec du déclenchement du webhook pour la course %s", course_id)


@transaction.atomic
def changer_statut(course_id, nouveau_statut, acteur=None, commentaire=""):
    course = Course.objects.select_for_update().get(id=course_id)
    ancien_statut = course.statut

    if nouveau_statut not in StatutCourse.values:
        raise TransitionInvalide(f"Statut inconnu : {nouveau_statut}")

    if not transition_est_autorisee(ancien_statut, nouveau_statut):
        raise TransitionInvalide(
            f"Impossible de passer de {ancien_statut} à {nouveau_statut}"
        )

    course.statut = nouveau_statut
    champs_modifies = ["statut"]

    if nouveau_statut == StatutCourse.LIVREE:
        course.date_livraison = timezone.now()
        champs_modifies.append("date_livraison")

    course.save(update_fields=champs_modifies)

    HistoriqueLivraison.objects.create(
        course=course,
        ancien_statut=ancien_statut,
        nouveau_statut=nouveau_statut,
        acteur=acteur,
        commentaire=commentaire,
    )

    transaction.on_commit(
        lambda: _notifier_partenaire(course.id, ancien_statut, nouveau_statut)
    )

    return course



def zone_est_utilisee(zone_id):
    """True si au moins une course utilise cette zone (départ ou arrivée)."""
    return Course.objects.filter(
        Q(zone_depart_id=zone_id) | Q(zone_arrivee_id=zone_id)
    ).exists()

@transaction.atomic
def assigner_course(course_id, livreur_id, acteur=None):
    # 1. Verrouiller la course
    course = Course.objects.select_for_update().get(id=course_id)

    # 2. La course doit être "creee"
    if course.statut != StatutCourse.CREEE:
        raise AffectationInvalide(
            f"Seule une course au statut 'creee' peut être affectée (statut actuel : {course.statut})"
        )

    # 3. Pas d'affectation existante
    if Affectation.objects.filter(course=course).exists():
        raise CourseDejaAffectee("Cette course a déjà une affectation")

    # 4. Le livreur doit exister, être actif et disponible
    from apps.accounts.models import Livreur  # import local

    try:
        livreur = Livreur.objects.get(id=livreur_id)
    except Livreur.DoesNotExist:
        raise LivreurNonEligible("Livreur introuvable")

    if not livreur.actif or not livreur.disponible:
        raise LivreurNonEligible("Ce livreur n'est pas actif ou pas disponible")

    # 5. Créer l'affectation et lier le livreur à la course
    Affectation.objects.create(
        course=course,
        livreur=livreur,
        statut=StatutAffectation.ACCEPTEE,
    )
    course.livreur = livreur
    course.save(update_fields=["livreur"])

    # 6. Changer le statut via le point d'écriture unique
    return changer_statut(
        course.id,
        StatutCourse.ACCEPTEE,
        acteur=acteur,
        commentaire=f"Affectation manuelle au livreur {livreur.id}",
    )