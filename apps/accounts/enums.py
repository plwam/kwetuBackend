from enum import Enum


class Role(str, Enum):
    ADMIN = 'ADMIN'
    PARTENAIRE = 'PARTENAIRE'
    LIVREUR = 'LIVREUR'

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name) for tag in cls]


class EtatCompte(str, Enum):
    CREE = 'CREE'
    ACTIF = 'ACTIF'
    DESACTIVE = 'DESACTIVE'
    REACTIVE = 'REACTIVE'
    SUPPRIME = 'SUPPRIME'

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name) for tag in cls]


class StatutCleAPI(str, Enum):
    ACTIVE = 'ACTIVE'
    REVOQUEE = 'REVOQUEE'

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name) for tag in cls]