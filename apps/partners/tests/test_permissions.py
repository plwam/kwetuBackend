"""Tests dédiés aux permissions, et contrôle de cohérence avec l'app accounts."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory

from apps.accounts.enums import Role
from apps.accounts.permissions import (
    EstAuthentifie,
    EstPartenaire,
    EstPartenaireOwner as EstPartenaireOwnerAccounts,
)
from apps.partners.permissions import EstPartenaireOwner

pytestmark = pytest.mark.django_db

User = get_user_model()
_factory = APIRequestFactory()


def _requete(user):
    """Fabrique une requête DRF minimale portant l'utilisateur donné."""
    request = _factory.get("/")
    request.user = user
    return request


def _livreur():
    return User.objects.create_user(
        email="livreur@test.com",
        nom="Martin",
        prenom="Pierre",
        telephone="+243770000000",
        role=Role.LIVREUR,
        password="pass123",
    )


class TestEstPartenaire:
    """La permission de rôle réutilisée depuis accounts."""

    def test_partenaire_autorise(self, partenaire):
        assert EstPartenaire().has_permission(_requete(partenaire.user), None) is True

    def test_livreur_refuse(self):
        assert EstPartenaire().has_permission(_requete(_livreur()), None) is False

    def test_anonyme_refuse(self):
        assert EstPartenaire().has_permission(_requete(AnonymousUser()), None) is False


class TestEstAuthentifie:
    """La permission générique d'accounts se comporte comme IsAuthenticated."""

    def test_partenaire_authentifie(self, partenaire):
        assert EstAuthentifie().has_permission(_requete(partenaire.user), None) is True

    def test_anonyme_refuse(self):
        assert EstAuthentifie().has_permission(_requete(AnonymousUser()), None) is False

    def test_coherent_avec_isauthenticated(self, partenaire):
        for user in (partenaire.user, _livreur(), AnonymousUser()):
            request = _requete(user)
            assert EstAuthentifie().has_permission(
                request, None
            ) == IsAuthenticated().has_permission(request, None)


class TestEstPartenaireOwnerPartners:
    """La permission de propriété locale à partners (doc partners §2.4)."""

    def test_proprietaire_autorise(self, partenaire, creer_course_factory):
        course = creer_course_factory(partenaire)
        assert (
            EstPartenaireOwner().has_object_permission(
                _requete(partenaire.user), None, course
            )
            is True
        )

    def test_autre_partenaire_refuse(
        self, partenaire, autre_partenaire, creer_course_factory
    ):
        course = creer_course_factory(autre_partenaire)
        assert (
            EstPartenaireOwner().has_object_permission(
                _requete(partenaire.user), None, course
            )
            is False
        )

    def test_utilisateur_sans_partenaire_refuse(self, creer_course_factory, partenaire):
        course = creer_course_factory(partenaire)
        assert (
            EstPartenaireOwner().has_object_permission(
                _requete(_livreur()), None, course
            )
            is False
        )


class TestCoherenceAvecAccounts:
    """Le doublon de nom doit au moins produire le MÊME verdict qu'accounts."""

    def test_meme_verdict_sur_sa_course(self, partenaire, creer_course_factory):
        course = creer_course_factory(partenaire)
        request = _requete(partenaire.user)
        assert EstPartenaireOwner().has_object_permission(
            request, None, course
        ) == EstPartenaireOwnerAccounts().has_object_permission(request, None, course)

    def test_meme_verdict_sur_course_d_autrui(
        self, partenaire, autre_partenaire, creer_course_factory
    ):
        course = creer_course_factory(autre_partenaire)
        request = _requete(partenaire.user)
        assert EstPartenaireOwner().has_object_permission(
            request, None, course
        ) == EstPartenaireOwnerAccounts().has_object_permission(request, None, course)
