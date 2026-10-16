def get_courses_du_partenaire(partenaire):
    """
    Queryset des courses appartenant au partenaire authentifié.

    Lecture optimisée : les zones sont jointes et l'historique préchargé pour
    éviter les requêtes N+1. L'import de ``Course`` est local pour respecter la
    règle anti-import-circulaire entre ``partners`` et ``courses``.
    """
    from apps.courses.models import Course

    return (
        Course.objects.filter(partenaire=partenaire)
        .select_related("zone_depart", "zone_arrivee")
        .prefetch_related("historique")
        .order_by("-date_creation")
    )
