"""Validation des fichiers de documents (livreurs).

Formats acceptés : **PDF, PNG, JPEG uniquement** (pas de SVG).
"""

import os

from django.conf import settings
from rest_framework import serializers

EXTENSIONS_AUTORISEES = (".pdf", ".png", ".jpg", ".jpeg")
TYPES_MIME_AUTORISES = ("application/pdf", "image/png", "image/jpeg", "image/jpg")
TAILLE_MAX_DOCUMENT_OCTETS = 5 * 1024 * 1024


def valider_fichier_document(fichier):
    """Valide l'extension, le type MIME et la taille d'un document.

    Lève ``serializers.ValidationError`` (donc un 400) si le fichier n'est pas
    un PDF, PNG ou JPEG, ou s'il dépasse la taille maximale autorisée.
    """
    if fichier is None:
        raise serializers.ValidationError("Aucun fichier fourni.")

    nom = (getattr(fichier, "name", "") or "").lower()
    extension = os.path.splitext(nom)[1]
    if extension not in EXTENSIONS_AUTORISEES:
        raise serializers.ValidationError(
            "Format non autorisé. Formats acceptés : pdf, png, jpeg."
        )

    type_mime = (getattr(fichier, "content_type", "") or "").lower()
    if type_mime and type_mime not in TYPES_MIME_AUTORISES:
        raise serializers.ValidationError("Type de fichier non autorisé.")

    taille_max = getattr(
        settings, "TAILLE_MAX_DOCUMENT_OCTETS", TAILLE_MAX_DOCUMENT_OCTETS
    )
    if fichier.size > taille_max:
        mo = taille_max // (1024 * 1024)
        raise serializers.ValidationError(
            f"Fichier trop volumineux (maximum {mo} Mo)."
        )
    return fichier
