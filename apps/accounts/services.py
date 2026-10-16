from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .enums import Role, StatutCleAPI, StatutDocument
from .exceptions import (
    AncienMotDePasseInvalide,
    CleAPIInvalide,
    EmailDejaUtilise,
    MotDePasseIdentique,
)
from .models import CleAPI, DocumentLivreur, DocumentRequis, Livreur, Partenaire

User = get_user_model()


@transaction.atomic
def creer_partenaire(data: dict) -> Partenaire:
    email = data["email"]
    if User.objects.filter(email=email).exists():
        raise EmailDejaUtilise()

    user = User.objects.create_user(
        email=email,
        nom=data["nom"],
        prenom=data["prenom"],
        telephone=data["telephone"],
        password=data["mot_de_passe"],
        role=Role.PARTENAIRE,
        actif=True,
        mot_de_passe_temporaire=True,
    )

    partenaire = Partenaire.objects.create(
        user=user,
        nom_boutique=data["nom_boutique"],
        url_webhook=data.get("url_webhook"),
        actif=True,
    )

    _cle_api, cle_complete = generer_cle_api(partenaire)
    partenaire._cle_api_complete = cle_complete

    return partenaire


@transaction.atomic
def creer_livreur(data: dict) -> Livreur:
    email = data["email"]
    if User.objects.filter(email=email).exists():
        raise EmailDejaUtilise()

    user = User.objects.create_user(
        email=email,
        nom=data["nom"],
        prenom=data["prenom"],
        telephone=data["telephone"],
        password=data["mot_de_passe"],
        role=Role.LIVREUR,
        actif=True,
        mot_de_passe_temporaire=True,
    )

    livreur = Livreur.objects.create(
        user=user,
        disponible=False,
        actif=True,
        verifie=True,
    )

    return livreur


def generer_cle_api(partenaire: Partenaire) -> tuple[CleAPI, str]:
    CleAPI.objects.filter(partenaire=partenaire, statut=StatutCleAPI.ACTIVE).update(
        statut=StatutCleAPI.REVOQUEE, date_revocation=timezone.now()
    )

    cle_complete, hash_cle = CleAPI.generer_cle()
    # Format: pk_live_{prefix}_{secret} -> prefixe stocké: pk_live_{prefix}
    parts = cle_complete.split("_")
    prefixe = "_".join(parts[:3])

    cle_api = CleAPI.objects.create(
        partenaire=partenaire,
        prefixe=prefixe,
        hash_cle=hash_cle,
        statut=StatutCleAPI.ACTIVE,
    )

    return cle_api, cle_complete


def revoquer_cle_api(cle_api_id: int, admin_user: User) -> CleAPI:
    try:
        cle_api = CleAPI.objects.select_related("partenaire").get(id=cle_api_id)
    except CleAPI.DoesNotExist:
        raise CleAPIInvalide()

    if cle_api.statut == StatutCleAPI.REVOQUEE:
        raise CleAPIInvalide("Cette clé est déjà révoquée.")

    cle_api.revoquer()
    return cle_api


def desactiver_partenaire(partenaire_id: int, admin_user: User) -> Partenaire:
    try:
        partenaire = Partenaire.objects.select_related("user").get(id=partenaire_id)
    except Partenaire.DoesNotExist:
        raise Partenaire.DoesNotExist()

    if not admin_user.role == Role.ADMIN:
        raise PermissionError("Seul un administrateur peut désactiver un partenaire.")

    partenaire.actif = False
    partenaire.user.actif = False
    partenaire.save(update_fields=["actif"])
    partenaire.user.save(update_fields=["actif"])

    CleAPI.objects.filter(partenaire=partenaire, statut=StatutCleAPI.ACTIVE).update(
        statut=StatutCleAPI.REVOQUEE, date_revocation=timezone.now()
    )

    return partenaire


def reactiver_partenaire(partenaire_id: int, admin_user: User) -> Partenaire:
    try:
        partenaire = Partenaire.objects.select_related("user").get(id=partenaire_id)
    except Partenaire.DoesNotExist:
        raise Partenaire.DoesNotExist()

    if not admin_user.role == Role.ADMIN:
        raise PermissionError("Seul un administrateur peut réactiver un partenaire.")

    partenaire.actif = True
    partenaire.user.actif = True
    partenaire.save(update_fields=["actif"])
    partenaire.user.save(update_fields=["actif"])

    return partenaire


def desactiver_livreur(livreur_id: int, admin_user: User) -> Livreur:
    try:
        livreur = Livreur.objects.select_related("user").get(id=livreur_id)
    except Livreur.DoesNotExist:
        raise Livreur.DoesNotExist()

    if not admin_user.role == Role.ADMIN:
        raise PermissionError("Seul un administrateur peut désactiver un livreur.")

    livreur.actif = False
    livreur.user.actif = False
    livreur.save(update_fields=["actif"])
    livreur.user.save(update_fields=["actif"])

    return livreur


def reactiver_livreur(livreur_id: int, admin_user: User) -> Livreur:
    try:
        livreur = Livreur.objects.select_related("user").get(id=livreur_id)
    except Livreur.DoesNotExist:
        raise Livreur.DoesNotExist()

    if not admin_user.role == Role.ADMIN:
        raise PermissionError("Seul un administrateur peut réactiver un livreur.")

    livreur.actif = True
    livreur.user.actif = True
    livreur.disponible = False
    livreur.save(update_fields=["actif", "disponible"])
    livreur.user.save(update_fields=["actif"])

    return livreur


@transaction.atomic
def changer_mot_de_passe(
    user: User, ancien_mot_de_passe: str, nouveau_mot_de_passe: str
) -> None:
    """Change le mot de passe de l'utilisateur authentifié.

    Sécurité :
    - Vérifie l'ancien mot de passe (preuve d'identité, même si le token est volé)
    - Invalide TOUS les refresh tokens de l'utilisateur (force re-login partout)
    - Désactive le flag mot_de_passe_temporaire
    """
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    if not user.check_password(ancien_mot_de_passe):
        raise AncienMotDePasseInvalide()
    if user.check_password(nouveau_mot_de_passe):
        raise MotDePasseIdentique()

    user.set_password(nouveau_mot_de_passe)
    user.mot_de_passe_temporaire = False
    user.save(update_fields=["password", "mot_de_passe_temporaire"])

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def inscrire_livreur(email: str, mot_de_passe: str) -> Livreur:
    """Inscription autonome d'un livreur (signup public).

    Le profil User est volontairement laissé incomplet (``nom``, ``prenom``,
    ``telephone`` vides) : le livreur le complète ensuite via l'endpoint de
    profil. Le compte démarre **non vérifié**.
    """
    if User.objects.filter(email=email).exists():
        raise EmailDejaUtilise()

    user = User.objects.create_user(
        email=email,
        nom="",
        prenom="",
        telephone="",
        password=mot_de_passe,
        role=Role.LIVREUR,
        actif=True,
        mot_de_passe_temporaire=False,
    )
    return Livreur.objects.create(
        user=user,
        disponible=False,
        actif=True,
        verifie=False,
    )


@transaction.atomic
def completer_profil_livreur(user, data: dict) -> User:
    """Complète (ou met à jour) le profil User d'un livreur."""
    champs = ("nom", "prenom", "telephone")
    modifies = [champ for champ in champs if champ in data]
    if modifies:
        for champ in modifies:
            setattr(user, champ, data[champ])
        user.save(update_fields=modifies)
    return user


@transaction.atomic
def enregistrer_document(livreur, document_requis, fichier) -> DocumentLivreur:
    """Crée ou remplace le document d'un livreur pour un document requis.

    Un nouvel envoi repasse le document au statut ``en_attente`` et réinitialise
    le commentaire de l'admin.
    """
    document, _ = DocumentLivreur.objects.update_or_create(
        livreur=livreur,
        document_requis=document_requis,
        defaults={
            "fichier": fichier,
            "statut": StatutDocument.EN_ATTENTE,
            "commentaire": "",
            "date_validation": None,
        },
    )
    recalculer_verification(livreur)
    return document


def documents_obligatoires():
    """Documents requis actifs marqués comme obligatoires."""
    return DocumentRequis.objects.filter(actif=True, obligatoire=True)


def recalculer_verification(livreur) -> bool:
    """Recalcule ``livreur.verifie``.

    Le livreur devient vérifié dès que **tous** les documents obligatoires
    actifs ont un document validé par l'admin. S'il n'existe aucun document
    obligatoire, le statut n'est pas modifié automatiquement.
    """
    obligatoires = documents_obligatoires()
    if not obligatoires.exists():
        return livreur.verifie

    valides = set(
        DocumentLivreur.objects.filter(
            livreur=livreur, statut=StatutDocument.VALIDE
        ).values_list("document_requis_id", flat=True)
    )
    tous_valides = all(doc.id in valides for doc in obligatoires)

    if tous_valides != livreur.verifie:
        livreur.verifie = tous_valides
        livreur.save(update_fields=["verifie"])
    return livreur.verifie


@transaction.atomic
def valider_document(document, commentaire: str = "") -> DocumentLivreur:
    """L'admin valide un document ; la vérification du livreur est recalculée."""
    document.statut = StatutDocument.VALIDE
    document.commentaire = commentaire
    document.date_validation = timezone.now()
    document.save(update_fields=["statut", "commentaire", "date_validation"])
    recalculer_verification(document.livreur)
    return document


@transaction.atomic
def rejeter_document(document, commentaire: str = "") -> DocumentLivreur:
    """L'admin rejette un document ; la vérification du livreur est recalculée."""
    document.statut = StatutDocument.REJETE
    document.commentaire = commentaire
    document.date_validation = timezone.now()
    document.save(update_fields=["statut", "commentaire", "date_validation"])
    recalculer_verification(document.livreur)
    return document


@transaction.atomic
def changer_verification(livreur, verifie: bool) -> Livreur:
    """Bascule manuelle du statut de vérification par l'administrateur.

    Permet à l'admin de vérifier (ou de retirer la vérification d') un livreur
    indépendamment de l'état des documents.
    """
    livreur.verifie = bool(verifie)
    livreur.save(update_fields=["verifie"])
    return livreur
