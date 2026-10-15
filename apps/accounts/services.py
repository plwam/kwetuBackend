from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .enums import Role, StatutCleAPI
from .exceptions import CleAPIInvalide, EmailDejaUtilise
from .models import CleAPI, Livreur, Partenaire

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
    )

    livreur = Livreur.objects.create(
        user=user,
        disponible=False,
        actif=True,
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
