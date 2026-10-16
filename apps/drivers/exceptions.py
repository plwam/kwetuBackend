class ErreurLivreur(Exception):
    """Classe mère des erreurs de l'espace livreur."""
    code = "erreur_livreur"
    statut_http = 400
    detail_par_defaut = "Une erreur est survenue."

    def __init__(self, detail=None):
        self.detail = detail or self.detail_par_defaut
        super().__init__(self.detail)

class CourseIntrouvable(ErreurLivreur):
    code = "course_introuvable"
    statut_http = 404
    detail_par_defaut = "Cette course est introuvable."

class CourseNonAssignee(ErreurLivreur):
    code = "course_non_assignee"
    statut_http = 403
    detail_par_defaut = "Cette course ne vous est pas assignée."

class CodeIncorrect(ErreurLivreur):
    code = "code_incorrect"
    statut_http = 400
    detail_par_defaut = "Le code de confirmation est incorrect."
    
class LivraisonBloquee(ErreurLivreur):
    code = "livraison_bloquee"
    statut_http = 429
    detail_par_defaut = (
        "Trop de codes incorrects. La confirmation de cette livraison "
        "est bloquée temporairement."
    )
class PaiementImpossible(ErreurLivreur):
    code = "paiement_impossible"
    statut_http = 400
    detail_par_defaut = (
        "Le paiement ne peut être enregistré que pour une course récupérée "
        "ou livrée."
    )
