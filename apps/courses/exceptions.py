class CoursesError(Exception):
    """Erreur de base du module courses."""


class TransitionInvalide(CoursesError):
    """Levée quand une transition de statut n'est pas autorisée."""


class ConflitConcurrence(CoursesError):
    """Levée quand deux opérations entrent en conflit sur la même course."""


class AffectationInvalide(CoursesError):
    """L'affectation demandée n'est pas possible (course pas dans le bon statut, etc.)."""


class CourseDejaAffectee(CoursesError):
    """La course possède déjà une affectation."""


class LivreurNonEligible(CoursesError):
    """Le livreur n'existe pas, est inactif ou n'est pas disponible."""