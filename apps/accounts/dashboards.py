"""Statistiques des dashboards, calculées côté backend selon le rôle."""

from decimal import Decimal

from django.db.models import Count, Q, Sum

from .enums import StatutDocument
from .models import DocumentLivreur, DocumentRequis, Livreur, Partenaire


def _arrondi(valeur) -> str:
    return str((valeur or Decimal("0.00")).quantize(Decimal("0.01")))


def _compteurs_courses(qs) -> dict:
    from apps.courses.enums import StatutCourse

    return qs.aggregate(
        total=Count("id"),
        creees=Count("id", filter=Q(statut=StatutCourse.CREEE)),
        acceptees=Count("id", filter=Q(statut=StatutCourse.ACCEPTEE)),
        recuperees=Count("id", filter=Q(statut=StatutCourse.RECUPEREE)),
        livrees=Count("id", filter=Q(statut=StatutCourse.LIVREE)),
        annulees=Count("id", filter=Q(statut=StatutCourse.ANNULEE)),
    )


def stats_admin() -> dict:
    """Vue d'ensemble plateforme pour l'administrateur."""
    from apps.courses.enums import StatutCourse
    from apps.courses.models import Course
    from apps.logistics.models import Tarif, Zone

    chiffre = Course.objects.filter(statut=StatutCourse.LIVREE).aggregate(
        total=Sum("prix_usd")
    )["total"]

    return {
        "courses": _compteurs_courses(Course.objects.all()),
        "chiffre_affaires_usd": _arrondi(chiffre),
        "partenaires": {
            "total": Partenaire.objects.count(),
            "actifs": Partenaire.objects.filter(actif=True).count(),
        },
        "livreurs": {
            "total": Livreur.objects.count(),
            "verifies": Livreur.objects.filter(verifie=True).count(),
            "non_verifies": Livreur.objects.filter(verifie=False).count(),
            "actifs": Livreur.objects.filter(actif=True).count(),
        },
        "zones": Zone.objects.count(),
        "tarifs": Tarif.objects.count(),
        "documents_en_attente": DocumentLivreur.objects.filter(
            statut=StatutDocument.EN_ATTENTE
        ).count(),
    }


def stats_partenaire(partenaire) -> dict:
    """Vue d'ensemble des courses propres à un partenaire."""
    from apps.courses.enums import StatutCourse
    from apps.courses.models import Course

    qs = Course.objects.filter(partenaire=partenaire)
    depenses = qs.filter(statut=StatutCourse.LIVREE).aggregate(total=Sum("prix_usd"))[
        "total"
    ]

    return {
        "courses": _compteurs_courses(qs),
        "depenses_usd": _arrondi(depenses),
    }


def stats_livreur(livreur) -> dict:
    """Vue d'ensemble de l'activité et du dossier d'un livreur."""
    from django.utils import timezone

    from apps.courses.enums import StatutCourse
    from apps.courses.models import Course

    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)

    disponibles = Course.objects.filter(
        statut=StatutCourse.CREEE, livreur__isnull=True
    ).count()
    en_cours = Course.objects.filter(
        livreur=livreur,
        statut__in=(StatutCourse.ACCEPTEE, StatutCourse.RECUPEREE),
    ).count()
    livrees_jour = Course.objects.filter(
        livreur=livreur,
        statut=StatutCourse.LIVREE,
        date_livraison__gte=debut,
    )
    total_jour = livrees_jour.aggregate(nombre=Count("id"), total=Sum("prix_usd"))

    obligatoires = DocumentRequis.objects.filter(actif=True, obligatoire=True)
    valides = set(
        DocumentLivreur.objects.filter(
            livreur=livreur, statut=StatutDocument.VALIDE
        ).values_list("document_requis_id", flat=True)
    )

    return {
        "verifie": livreur.verifie,
        "actif": livreur.actif,
        "disponible": livreur.disponible,
        "profil_complet": bool(
            livreur.user.nom and livreur.user.prenom and livreur.user.telephone
        ),
        "courses": {
            "disponibles": disponibles,
            "en_cours": en_cours,
            "livrees_aujourd_hui": total_jour["nombre"],
        },
        "gains_du_jour_usd": _arrondi(total_jour["total"]),
        "documents": {
            "requis_obligatoires": obligatoires.count(),
            "valides": len([doc for doc in obligatoires if doc.id in valides]),
        },
    }
