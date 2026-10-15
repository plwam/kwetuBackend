from decimal import Decimal

from django.db import models, transaction

from apps.logistics.exceptions import TarifIntrouvable
from apps.logistics.models import StatutZone, Tarif, Zone


def calculer_prix(zone_depart_id: int, zone_arrivee_id: int) -> Decimal:
    """
    Calcule le prix d'un trajet entre deux zones.

    Args:
        zone_depart_id: ID de la zone de départ.
        zone_arrivee_id: ID de la zone d'arrivée.

    Returns:
        Le prix en USD (Decimal).

    Raises:
        TarifIntrouvable: Si aucun tarif actif n'existe pour ce couple.
    """
    try:
        tarif = Tarif.objects.get(
            zone_depart_id=zone_depart_id,
            zone_arrivee_id=zone_arrivee_id,
            actif=True,
        )
    except Tarif.DoesNotExist:
        raise TarifIntrouvable(
            f"Aucun tarif actif pour les zones {zone_depart_id} → {zone_arrivee_id}"
        )
    return tarif.prix_usd


def zone_est_utilisee(zone_id: int) -> bool:
    """
    Vérifie si une zone est référencée par au moins une course.

    Args:
        zone_id: ID de la zone à vérifier.

    Returns:
        True si la zone est utilisée (en départ ou arrivée), False sinon.
    """
    from apps.courses.models import Course

    return Course.objects.filter(
        models.Q(zone_depart_id=zone_id) | models.Q(zone_arrivee_id=zone_id)
    ).exists()


@transaction.atomic
def creer_zone(nom: str, description: str = "") -> Zone:
    """
    Crée une nouvelle zone avec le statut ACTIVE.

    Args:
        nom: Nom unique de la zone.
        description: Description optionnelle.

    Returns:
        L'instance Zone créée.

    Raises:
        ValidationError: Si le nom est déjà utilisé.
    """
    return Zone.objects.create(
        nom=nom,
        description=description,
        statut=StatutZone.ACTIVE,
    )


@transaction.atomic
def modifier_tarif(
    tarif: Tarif,
    prix_usd: Decimal = None,
    actif: bool = None,
) -> Tarif:
    """
    Modifie un tarif existant.

    Args:
        tarif: L'instance Tarif à modifier.
        prix_usd: Nouveau prix (optionnel).
        actif: Nouveau statut (optionnel).

    Returns:
        L'instance Tarif modifiée.
    """
    if prix_usd is not None:
        tarif.prix_usd = prix_usd
    if actif is not None:
        tarif.actif = actif
    tarif.save()
    return tarif