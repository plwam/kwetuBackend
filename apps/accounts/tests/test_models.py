import pytest
from django.contrib.auth import get_user_model

from apps.accounts.enums import Role, StatutCleAPI
from apps.accounts.models import CleAPI, Livreur, Partenaire

User = get_user_model()


@pytest.fixture
def user_partenaire():
    return User.objects.create_user(
        email="partenaire@test.com",
        nom="Dupont",
        prenom="Jean",
        telephone="+243888888888",
        role=Role.PARTENAIRE,
        password="pass123",
    )


@pytest.fixture
def user_livreur():
    return User.objects.create_user(
        email="livreur@test.com",
        nom="Martin",
        prenom="Pierre",
        telephone="+243777777777",
        role=Role.LIVREUR,
        password="pass123",
    )


@pytest.fixture
def partenaire(user_partenaire):
    return Partenaire.objects.create(
        user=user_partenaire,
        nom_boutique="Boutique Test",
        url_webhook="https://test.com/webhook",
    )


@pytest.mark.django_db
class TestUserModel:
    def test_creer_user_admin(self):
        user = User.objects.create_superuser(
            email="admin@test.com",
            nom="Admin",
            prenom="Super",
            telephone="+243999999999",
            password="admin123",
        )
        assert user.role == Role.ADMIN
        assert user.actif is True
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_creer_user_partenaire(self):
        user = User.objects.create_user(
            email="partenaire@test.com",
            nom="Dupont",
            prenom="Jean",
            telephone="+243888888888",
            role=Role.PARTENAIRE,
            password="pass123",
        )
        assert user.role == Role.PARTENAIRE
        assert user.est_partenaire() is True
        assert user.est_admin() is False

    def test_creer_user_livreur(self):
        user = User.objects.create_user(
            email="livreur@test.com",
            nom="Martin",
            prenom="Pierre",
            telephone="+243777777777",
            role=Role.LIVREUR,
            password="pass123",
        )
        assert user.role == Role.LIVREUR
        assert user.est_livreur() is True

    def test_email_unique(self):
        User.objects.create_user(
            email="test@test.com",
            nom="Test",
            prenom="User",
            telephone="+243111111111",
            role=Role.PARTENAIRE,
            password="pass123",
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                email="test@test.com",
                nom="Test2",
                prenom="User2",
                telephone="+243222222222",
                role=Role.LIVREUR,
                password="pass123",
            )


@pytest.mark.django_db
class TestPartenaireModel:
    def test_creer_partenaire(self, user_partenaire):
        partenaire = Partenaire.objects.create(
            user=user_partenaire,
            nom_boutique="Ma Boutique",
            url_webhook="https://maboutique.com/webhook",
        )
        assert partenaire.nom_boutique == "Ma Boutique"
        assert partenaire.actif is True

    def test_cle_api_active(self, partenaire):
        cle = CleAPI.objects.create(
            partenaire=partenaire,
            prefixe="pk_live_test",
            hash_cle="hash123",
            statut=StatutCleAPI.ACTIVE,
        )
        assert partenaire.cle_api_active() == cle


@pytest.mark.django_db
class TestLivreurModel:
    def test_creer_livreur(self, user_livreur):
        livreur = Livreur.objects.create(user=user_livreur)
        assert livreur.disponible is False
        assert livreur.actif is True


@pytest.mark.django_db
class TestCleAPIModel:
    def test_generer_cle(self):
        cle_complete, hash_cle = CleAPI.generer_cle()
        assert cle_complete.startswith("pk_live_")
        assert len(hash_cle) == 64

    def test_hasher_cle(self):
        cle = "pk_live_test_secret"
        hash1 = CleAPI.hasher_cle(cle)
        hash2 = CleAPI.hasher_cle(cle)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_verifier_cle(self, partenaire):
        cle_complete, hash_cle = CleAPI.generer_cle()
        prefixe = cle_complete.split("_")[0] + "_" + cle_complete.split("_")[1]
        cle_api = CleAPI.objects.create(
            partenaire=partenaire,
            prefixe=prefixe,
            hash_cle=hash_cle,
            statut=StatutCleAPI.ACTIVE,
        )
        assert cle_api.verifier_cle(cle_complete) is True
        assert cle_api.verifier_cle("mauvaise_cle") is False

    def test_revoquer(self, partenaire):
        cle_complete, hash_cle = CleAPI.generer_cle()
        prefixe = cle_complete.split("_")[0] + "_" + cle_complete.split("_")[1]
        cle_api = CleAPI.objects.create(
            partenaire=partenaire,
            prefixe=prefixe,
            hash_cle=hash_cle,
            statut=StatutCleAPI.ACTIVE,
        )
        cle_api.revoquer()
        cle_api.refresh_from_db()
        assert cle_api.statut == StatutCleAPI.REVOQUEE
        assert cle_api.date_revocation is not None
