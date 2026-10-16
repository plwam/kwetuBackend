import hmac
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.utils import timezone
from apps.courses.enums import StatutAffectation, StatutCourse
from apps.courses.exceptions import ConflitConcurrence, TransitionInvalide
from apps.courses.models import Affectation, Course
from apps.courses.services import changer_statut
from apps.drivers.exceptions import (
    CodeIncorrect,
    CourseIntrouvable,
    CourseNonAssignee,
    LivraisonBloquee,
    PaiementImpossible,
)

STATUTS_EN_COURS = (StatutCourse.ACCEPTEE, StatutCourse.RECUPEREE)
STATUTS_PAIEMENT_POSSIBLE = (StatutCourse.RECUPEREE, StatutCourse.LIVREE)

def _nombre_maximal_tentatives():
    """0 désactive la limitation des tentatives de code."""
    return getattr(settings, "DRIVERS_MAX_TENTATIVES_CODE", 3)

def _duree_blocage_en_secondes():
    return getattr(settings, "DRIVERS_DUREE_BLOCAGE_SECONDES", 900)
# -------------------------------------------------------------------------
# Fonctions internes
# -------------------------------------------------------------------------

def _charger_course_verrouillee(course_id):
    """Charge la course avec un verrou de ligne (à appeler dans une transaction)."""
    try:
        return Course.objects.select_for_update().get(id=course_id)
    except Course.DoesNotExist:
        raise CourseIntrouvable()

def _verifier_propriete(course, livreur):
    """Seul le livreur affecté à la course peut agir dessus."""
    if course.livreur_id != livreur.id:
        raise CourseNonAssignee()
    
def _cle_compteur_tentatives(course, livreur):
    return f"drivers:livraison:{course.id}:{livreur.id}"
    
def _verifier_livraison_non_bloquee(course, livreur):
    maximum = _nombre_maximal_tentatives()
    
    if maximum <= 0:
        return
    if cache.get(_cle_compteur_tentatives(course, livreur), 0) >= maximum:
        raise LivraisonBloquee()

def _enregistrer_echec_code(course, livreur):
    """Compte un code faux ; renvoie le nombre de tentatives restantes (ou None)."""
    maximum = _nombre_maximal_tentatives()
    if maximum <= 0:
         return None
    cle = _cle_compteur_tentatives(course, livreur)
    cache.add(cle, 0, timeout=_duree_blocage_en_secondes())
    
    try:
        echecs = cache.incr(cle)
    
    except ValueError:  # la clé a expiré entre-temps
        cache.set(cle, 1, timeout=_duree_blocage_en_secondes())
        echecs = 1
    
    if echecs >= maximum:
# le blocage dure à partir du dernier échec
        cache.set(cle, echecs, timeout=_duree_blocage_en_secondes())
    
    return max(maximum - echecs, 0)

def _reinitialiser_compteur_tentatives(course, livreur):
    cache.delete(_cle_compteur_tentatives(course, livreur))

def _code_est_correct(code_saisi, code_attendu):
    """Comparaison en temps constant, après suppression des espaces."""
    saisi = (code_saisi or "").strip().encode("utf-8")
    attendu = str(code_attendu or "").encode("utf-8")
    
    if not attendu:
        return False
    return hmac.compare_digest(saisi, attendu)

def courses_disponibles():
    """CU-16 : courses créées, sans livreur, de la plus ancienne à la plus récente."""
    
    return (
        Course.objects.filter(statut=StatutCourse.CREEE, livreur__isnull=True)
        .select_related("zone_depart", "zone_arrivee")
        .order_by("date_creation", "id")
    )
def courses_en_cours_du_livreur(livreur):
    """Courses acceptées ou récupérées par ce livreur."""
    return (
        Course.objects.filter(livreur=livreur, statut__in=STATUTS_EN_COURS)
        .select_related("zone_depart", "zone_arrivee", "partenaire")
        .order_by("date_creation", "id")
    )

def _bornes_du_jour():
    """Début (inclus) et fin (exclue) de la journée locale en cours."""
    maintenant = timezone.localtime()
    debut = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    return debut, debut + timedelta(days=1)

def historique_du_jour(livreur):
    """CU-21 : courses livrées aujourd'hui par ce livreur, la plus récente d'abord."""
    debut, fin = _bornes_du_jour()
    
    return (
        Course.objects.filter(
            livreur=livreur,
            statut=StatutCourse.LIVREE,
            date_livraison__gte=debut,
            date_livraison__lt=fin,
        )
        .select_related("zone_depart", "zone_arrivee")
        .order_by("-date_livraison", "-id")
    )
def resume_du_jour(livreur):
    """Nombre de livraisons et total en USD sur TOUTE la journée (pas une page)."""
    totaux = historique_du_jour(livreur).aggregate(
        nombre=Count("id"), total=Sum("prix_usd")
    )
    total = totaux["total"] or Decimal("0.00")
    
    return {
        "nb_livrees": totaux["nombre"],
        "total_usd": str(total.quantize(Decimal("0.01"))),
    }
def date_du_jour():
    return timezone.localdate().isoformat()

@transaction.atomic
def accepter_course(course_id, livreur):
    """CU-17 : un seul livreur peut obtenir la course (verrou de ligne)."""
    course = _charger_course_verrouillee(course_id)
    
    if course.statut != StatutCourse.CREEE or course.livreur_id is not None:
        raise ConflitConcurrence("Cette course n'est plus disponible.")
    try:
        with transaction.atomic():
            Affectation.objects.create(
                course=course,
                livreur=livreur,
                statut=StatutAffectation.ACCEPTEE,
            )
    except IntegrityError:
        raise ConflitConcurrence("Cette course n'est plus disponible.")
    course.livreur = livreur
    course.save(update_fields=["livreur"])
    
    return changer_statut(course.id, StatutCourse.ACCEPTEE, acteur=livreur.user)

@transaction.atomic
def marquer_recupere(course_id, livreur):
    """CU-18 : le livreur a récupéré le colis chez le partenaire."""
    course = _charger_course_verrouillee(course_id)
    _verifier_propriete(course, livreur)
    
    if course.statut != StatutCourse.ACCEPTEE:
        raise TransitionInvalide(
            "Le colis ne peut être récupéré que pour une course acceptée."
        )
    return changer_statut(course.id, StatutCourse.RECUPEREE, acteur=livreur.user)

@transaction.atomic
def livrer_avec_code(course_id, livreur, code):
    """CU-19 : la livraison est confirmée avec le code donné par le destinataire."""
    course = _charger_course_verrouillee(course_id)
    _verifier_propriete(course, livreur)
    
    if course.statut != StatutCourse.RECUPEREE:
        raise TransitionInvalide(
            "La livraison ne peut être confirmée que pour une course récupérée."
        )
    _verifier_livraison_non_bloquee(course, livreur)
    
    if not _code_est_correct(code, course.code_confirmation):
        restantes = _enregistrer_echec_code(course, livreur)
        
        if restantes is None:
            raise CodeIncorrect()
        
        if restantes == 0:
            raise CodeIncorrect(
                "Le code de confirmation est incorrect. La confirmation de "
                "cette livraison est maintenant bloquée temporairement."
            )
        raise CodeIncorrect(
            f"Le code de confirmation est incorrect. "
            f"Il vous reste {restantes} tentative(s)."
        )
    
    _reinitialiser_compteur_tentatives(course, livreur)
    
    course = changer_statut(course.id, StatutCourse.LIVREE, acteur=livreur.user)
    # Filet de sécurité : si courses n'a pas renseigné la date de livraison,
    # on la renseigne pour que l'historique du jour soit exact.
    
    if course.date_livraison is None:
        course.date_livraison = timezone.now()
        course.save(update_fields=["date_livraison"])
    return course 

@transaction.atomic
def marquer_paye(course_id, livreur):
    """CU-20 : le paiement a été encaissé. Idempotent, sans retour arrière."""
    course = _charger_course_verrouillee(course_id)
    _verifier_propriete(course, livreur)
    
    if course.statut not in STATUTS_PAIEMENT_POSSIBLE:
        raise PaiementImpossible()
    
    if not course.paye:
        course.paye = True
        course.save(update_fields=["paye"])
    return course