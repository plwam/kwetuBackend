class CoursesError(Exception):
    """Erreur de base du module courses."""


class TransitionInvalide(CoursesError):
    """Levée quand une transition de statut n'est pas autorisée."""


class ConflitConcurrence(CoursesError):
    """Levée quand deux opérations entrent en conflit sur la même course."""