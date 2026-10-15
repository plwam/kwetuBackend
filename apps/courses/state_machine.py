from apps.courses.enums import StatutCourse

TRANSITIONS_AUTORISEES = {
    StatutCourse.CREEE: [StatutCourse.ACCEPTEE, StatutCourse.ANNULEE],
    StatutCourse.ACCEPTEE: [StatutCourse.RECUPEREE, StatutCourse.ANNULEE],
    StatutCourse.RECUPEREE: [StatutCourse.LIVREE],
    StatutCourse.LIVREE: [],
    StatutCourse.ANNULEE: [],
}


def transition_est_autorisee(ancien_statut, nouveau_statut):
    """Retourne True si on peut passer de ancien_statut à nouveau_statut."""
    return nouveau_statut in TRANSITIONS_AUTORISEES.get(ancien_statut, [])