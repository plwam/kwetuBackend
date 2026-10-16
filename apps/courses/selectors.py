from django.db.models import Count, Q
from django.utils import timezone

from apps.courses.enums import StatutCourse
from apps.courses.models import Course


def get_courses_du_jour():
    """Courses créées aujourd'hui (selon le fuseau horaire de settings.TIME_ZONE)."""
    return Course.objects.filter(date_creation__date=timezone.localdate())


def get_courses_admin(filtres=None):
    """Liste des courses pour l'admin, avec filtres optionnels."""
    filtres = filtres or {}
    qs = Course.objects.select_related(
        "partenaire", "livreur", "zone_depart", "zone_arrivee"
    )

    if filtres.get("statut") in StatutCourse.values:
        qs = qs.filter(statut=filtres["statut"])
    if filtres.get("partenaire"):
        qs = qs.filter(partenaire_id=filtres["partenaire"])
    if filtres.get("livreur"):
        qs = qs.filter(livreur_id=filtres["livreur"])
    if filtres.get("zone"):
        qs = qs.filter(
            Q(zone_depart_id=filtres["zone"]) | Q(zone_arrivee_id=filtres["zone"])
        )
    if filtres.get("date"):
        qs = qs.filter(date_creation__date=filtres["date"])  # format AAAA-MM-JJ

    return qs


def get_stats_dashboard():
    """Compteurs du jour par statut."""
    return get_courses_du_jour().aggregate(
        total=Count("id"),
        creees=Count("id", filter=Q(statut=StatutCourse.CREEE)),
        acceptees=Count("id", filter=Q(statut=StatutCourse.ACCEPTEE)),
        recuperees=Count("id", filter=Q(statut=StatutCourse.RECUPEREE)),
        livrees=Count("id", filter=Q(statut=StatutCourse.LIVREE)),
        annulees=Count("id", filter=Q(statut=StatutCourse.ANNULEE)),
    )