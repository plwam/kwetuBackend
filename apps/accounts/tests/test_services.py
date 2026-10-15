import pytest
from django.contrib.auth import get_user_model

from apps.accounts.enums import Role, StatutCleAPI
from apps.accounts.exceptions import CleAPIInvalide, EmailDejaUtilise
from apps.accounts.models import Livreur, Partenaire
from apps.accounts.services import (
    creer_livreur,
    creer_partenaire,
    desactiver_livreur,
    desactiver_partenaire,
    generer_cle_api,
    reactiver_livreur,
    reactiver_partenaire,
    revoquer_cle_api,
)

User = get_user_model()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email='admin@test.com',
        nom='Admin',
        prenom='Super',
        telephone='+243999999999',
        password='admin123'
    )


@pytest.mark.django_db
class TestCreerPartenaire:
    def test_creer_partenaire_succes(self, admin_user):
        data = {
            'email': 'partenaire@test.com',
            'nom': 'Dupont',
            'prenom': 'Jean',
            'telephone': '+243888888888',
            'mot_de_passe': 'pass123',
            'nom_boutique': 'Ma Boutique',
            'url_webhook': 'https://maboutique.com/webhook'
        }
        partenaire = creer_partenaire(data)
        assert partenaire.nom_boutique == 'Ma Boutique'
        assert partenaire.user.role == Role.PARTENAIRE
        assert partenaire.actif is True
        assert hasattr(partenaire, '_cle_api_complete')
        assert partenaire._cle_api_complete.startswith('pk_live_')

    def test_creer_partenaire_email_deja_utilise(self, admin_user):
        User.objects.create_user(
            email='existing@test.com',
            nom='Exist',
            prenom='User',
            telephone='+243111111111',
            role=Role.PARTENAIRE,
            password='pass123'
        )
        data = {
            'email': 'existing@test.com',
            'nom': 'Dupont',
            'prenom': 'Jean',
            'telephone': '+243888888888',
            'mot_de_passe': 'pass123',
            'nom_boutique': 'Ma Boutique'
        }
        with pytest.raises(EmailDejaUtilise):
            creer_partenaire(data)

    def test_creer_partenaire_nom_boutique_unique(self, admin_user):
        user1 = User.objects.create_user(
            email='p1@test.com', nom='P1', prenom='Un',
            telephone='+243111111111', role=Role.PARTENAIRE, password='pass123'
        )
        Partenaire.objects.create(user=user1, nom_boutique='Boutique Unique')

        data = {
            'email': 'p2@test.com',
            'nom': 'P2',
            'prenom': 'Deux',
            'telephone': '+243222222222',
            'mot_de_passe': 'pass123',
            'nom_boutique': 'Boutique Unique'
        }
        with pytest.raises(Exception):
            creer_partenaire(data)


@pytest.mark.django_db
class TestCreerLivreur:
    def test_creer_livreur_succes(self, admin_user):
        data = {
            'email': 'livreur@test.com',
            'nom': 'Martin',
            'prenom': 'Pierre',
            'telephone': '+243777777777',
            'mot_de_passe': 'pass123'
        }
        livreur = creer_livreur(data)
        assert livreur.user.role == Role.LIVREUR
        assert livreur.disponible is False
        assert livreur.actif is True


@pytest.mark.django_db
class TestGenererCleAPI:
    def test_generer_cle_api(self, admin_user):
        user = User.objects.create_user(
            email='partenaire@test.com', nom='Dupont', prenom='Jean',
            telephone='+243888888888', role=Role.PARTENAIRE, password='pass123'
        )
        partenaire = Partenaire.objects.create(user=user, nom_boutique='Boutique Test')
        cle_api, cle_complete = generer_cle_api(partenaire)
        assert cle_api.partenaire == partenaire
        assert cle_api.statut == StatutCleAPI.ACTIVE
        assert cle_complete.startswith('pk_live_')

    def test_generer_cle_api_revoque_ancienne(self, admin_user):
        user = User.objects.create_user(
            email='partenaire@test.com', nom='Dupont', prenom='Jean',
            telephone='+243888888888', role=Role.PARTENAIRE, password='pass123'
        )
        partenaire = Partenaire.objects.create(user=user, nom_boutique='Boutique Test')
        cle1, _ = generer_cle_api(partenaire)
        cle2, _ = generer_cle_api(partenaire)
        cle1.refresh_from_db()
        cle2.refresh_from_db()
        assert cle1.statut == StatutCleAPI.REVOQUEE
        assert cle2.statut == StatutCleAPI.ACTIVE


@pytest.mark.django_db
class TestRevoquerCleAPI:
    def test_revoquer_cle_api(self, admin_user):
        user = User.objects.create_user(
            email='partenaire@test.com', nom='Dupont', prenom='Jean',
            telephone='+243888888888', role=Role.PARTENAIRE, password='pass123'
        )
        partenaire = Partenaire.objects.create(user=user, nom_boutique='Boutique Test')
        cle_api, _ = generer_cle_api(partenaire)
        revoquer_cle_api(cle_api.id, admin_user)
        cle_api.refresh_from_db()
        assert cle_api.statut == StatutCleAPI.REVOQUEE

    def test_revoquer_cle_deja_revoquee(self, admin_user):
        user = User.objects.create_user(
            email='partenaire@test.com', nom='Dupont', prenom='Jean',
            telephone='+243888888888', role=Role.PARTENAIRE, password='pass123'
        )
        partenaire = Partenaire.objects.create(user=user, nom_boutique='Boutique Test')
        cle_api, _ = generer_cle_api(partenaire)
        revoquer_cle_api(cle_api.id, admin_user)
        with pytest.raises(CleAPIInvalide):
            revoquer_cle_api(cle_api.id, admin_user)


@pytest.mark.django_db
class TestDesactiverReactiverPartenaire:
    def test_desactiver_partenaire(self, admin_user):
        user = User.objects.create_user(
            email='partenaire@test.com', nom='Dupont', prenom='Jean',
            telephone='+243888888888', role=Role.PARTENAIRE, password='pass123'
        )
        partenaire = Partenaire.objects.create(user=user, nom_boutique='Boutique Test')
        generer_cle_api(partenaire)

        desactiver_partenaire(partenaire.id, admin_user)
        partenaire.refresh_from_db()
        assert partenaire.actif is False
        assert partenaire.user.actif is False
        assert partenaire.cles_api.filter(statut=StatutCleAPI.ACTIVE).count() == 0

    def test_reactiver_partenaire(self, admin_user):
        user = User.objects.create_user(
            email='partenaire@test.com', nom='Dupont', prenom='Jean',
            telephone='+243888888888', role=Role.PARTENAIRE, password='pass123'
        )
        partenaire = Partenaire.objects.create(user=user, nom_boutique='Boutique Test')
        desactiver_partenaire(partenaire.id, admin_user)
        reactiver_partenaire(partenaire.id, admin_user)
        partenaire.refresh_from_db()
        assert partenaire.actif is True
        assert partenaire.user.actif is True


@pytest.mark.django_db
class TestDesactiverReactiverLivreur:
    def test_desactiver_livreur(self, admin_user):
        user = User.objects.create_user(
            email='livreur@test.com', nom='Martin', prenom='Pierre',
            telephone='+243777777777', role=Role.LIVREUR, password='pass123'
        )
        livreur = Livreur.objects.create(user=user, disponible=True)
        desactiver_livreur(livreur.id, admin_user)
        livreur.refresh_from_db()
        assert livreur.actif is False
        assert livreur.user.actif is False

    def test_reactiver_livreur(self, admin_user):
        user = User.objects.create_user(
            email='livreur@test.com', nom='Martin', prenom='Pierre',
            telephone='+243777777777', role=Role.LIVREUR, password='pass123'
        )
        livreur = Livreur.objects.create(user=user, disponible=True)
        desactiver_livreur(livreur.id, admin_user)
        reactiver_livreur(livreur.id, admin_user)
        livreur.refresh_from_db()
        assert livreur.actif is True
        assert livreur.user.actif is True
        assert livreur.disponible is False