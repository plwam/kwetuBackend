# MASHOP LIVRAISON — Consignes globales et architecture du projet

> Document de référence pour toute l'équipe backend.  
> À lire avant d'écrire la première ligne de code.  
> Toute dérogation doit être discutée et validée en équipe.

---

## Sommaire

1. Stack technique imposée
2. Environnements (développement / production)
3. Base de données
4. Documentation API (Swagger + ReDoc)
5. Cache et files d'attente (Redis + Celery)
6. Standard de réponse JSON
7. Standard de documentation des endpoints
8. Structure du projet
9. Conventions de nommage
10. Règles de collaboration Git
11. Checklist avant chaque merge
12. Architecture globale du projet

---

# 1. Stack technique imposée

## 1.1. Backend

| Composant | Technologie | Rôle |
|---|---|---|
| Framework web | **Django 5.x** | Structure principale |
| API REST | **Django REST Framework** | Serializers, vues, permissions |
| Authentification | **JWT (SimpleJWT)** + clé API | Deux mécanismes distincts |
| Base de données (dev) | **SQLite** | Léger, aucun serveur à installer |
| Base de données (prod) | **PostgreSQL** (priorité) ou **MySQL** | Robustesse, concurrence |
| Cache | **Redis** | Cache, sessions, rate limiting |
| File d'attente | **Celery** | Tâches longues (webhooks, notifications) |
| Broker Celery | **Redis** | File de messages |
| Documentation API | **drf-spectacular** (Swagger + ReDoc) | Interface interactive |
| Serveur HTTP (prod) | **Gunicorn** | App serveur WSGI |
| Reverse proxy (prod) | **Nginx** | Terminaison TLS, static files |
| Tests | **pytest + pytest-django** | Tests unitaires et intégration |
| Linting | **ruff** + **black** | Qualité et formatage du code |

## 1.2. Frontend (rappel, hors périmètre backend)

| Composant | Technologie |
|---|---|
| Framework | **React** |
| Consommation API | **fetch** ou **axios** |
| Authentification | Stockage du JWT côté client (mémoire + cookie httpOnly) |

---

# 2. Environnements (développement / production)

## 2.1. Séparation des settings

Le projet doit avoir **trois fichiers de settings** :

```text
config/settings/
├── base.py       # Commun à tous les environnements
├── dev.py        # Développement (SQLite, DEBUG=True)
└── prod.py       # Production (PostgreSQL, DEBUG=False)
```
# Développement
export DJANGO_SETTINGS_MODULE=config.settings.dev

# Production
export DJANGO_SETTINGS_MODULE=config.settings.prod

# 2.2. Tableau comparatif des environnements
Aspect	Développement (dev.py)	Production (prod.py)
DEBUG	True	False
Base de données	SQLite	PostgreSQL (ou MySQL)
ALLOWED_HOSTS	["*"]	Liste explicite des domaines
Cache	Local (en mémoire) ou Redis local	Redis
Celery	Mode eager (exécution synchrone)	Workers réels
HTTPS	Non requis	Obligatoire (via Nginx)
Logs	Console	Fichiers + rotation
Emails	Console (EMAIL_BACKEND = console)	SMTP réel
Fichiers statiques	Servis par Django	Servis par Nginx
Swagger / ReDoc	Accessibles	Accessibles uniquement aux ADMIN ou protégés
2.3. Variables d'environnement (obligatoires)
Aucun secret ne doit être écrit dans le code. Tous passent par des variables d'environnement (.env en dev, secrets manager en prod).

Liste minimale :

# Variable	Description	Exemple
DJANGO_SECRET_KEY	Clé secrète Django	django-insecure-xxxx
DJANGO_SETTINGS_MODULE	Fichier de settings	config.settings.dev
DATABASE_URL	URL de connexion BDD	postgres://user:pass@host:5432/db
REDIS_URL	URL Redis	redis://localhost:6379/0
CELERY_BROKER_URL	Broker Celery	redis://localhost:6379/1
JWT_SIGNING_KEY	Clé de signature JWT	(différent de SECRET_KEY)
JWT_ACCESS_LIFETIME	Durée access token (minutes)	30
JWT_REFRESH_LIFETIME	Durée refresh token (jours)	7
ALLOWED_HOSTS	Hôtes autorisés (prod)	api.mashop.cd
CORS_ALLOWED_ORIGINS	Domaines frontend autorisés

#3.2. Règles de migration
Toujours créer une migration après modification d'un modèle :

bash
python manage.py makemigrations <nom_app>
Jamais modifier une migration déjà appliquée en production.

Toujours tester les migrations sur une copie de la base de prod avant déploiement.

Jamais mélanger les migrations de plusieurs apps dans un même commit.

Toujours nommer les migrations de façon explicite quand elles sont complexes :

bash
python manage.py makemigrations <nom_app> --name ajout_champ_etat_compte

# 4. Documentation API (Swagger + ReDoc)
## 4.1. Bibliothèque retenue
drf-spectacular — remplace l'ancien drf-yasg (non maintenu).

Installation :

bash
pip install drf-spectacular
## 4.2. URLs exposées
URL	Interface	Usage
/api/schema/	Schéma OpenAPI 3.0 (JSON/YAML)	Consommé par les outils
/api/docs/	Swagger UI	Interface interactive (tests + lecture)
/api/redoc/	ReDoc	Documentation lisible et structurée
Toutes ces URLs sont accessibles uniquement aux ADMIN authentifiés (sauf en développement). Aucune documentation API ne doit être publique en production.

## 4.3. Ce que chaque endpoint doit documenter
Pour chaque endpoint, la documentation générée doit préciser :

Élément	Obligatoire
Description courte	✅
Description longue (contexte, cas d'usage)	✅
Mécanisme d'authentification (JWT / clé API / aucune)	✅
Rôles autorisés (ADMIN / PARTENAIRE / LIVREUR)	✅
Paramètres de requête (path, query, body)	✅
Exemple de requête JSON	✅
Exemple de réponse succès JSON	✅
Exemple de réponse erreur JSON	✅
Codes HTTP possibles	✅
Restrictions d'accès (propriété, portée)	✅


6.2. Format d'erreur
Toute réponse d'erreur doit respecter ce format :

json
{
  "success": false,
  "data": null,
  "error": {
    "code": "identifiant_technique",
    "detail": "Message lisible par un humain"
  }
}
code est un identifiant technique en anglais, en snake_case.

detail est un message en français, compréhensible par un utilisateur.

data est toujours null en cas d'erreur.

6.3. Format de pagination
Quand un endpoint retourne une liste, la réponse inclut la pagination :

```json
{
  "success": true,
  "data": {
    "count": 42,
    "next": "https://api.mashop.cd/api/v1/admin/partenaires/?page=3",
    "previous": "https://api.mashop.cd/api/v1/admin/partenaires/?page=1",
    "results": [ ]
  },
  "error": null
}```


6.7. Encodage
Toutes les réponses sont encodées en UTF-8 avec l'en-tête :

text
Content-Type: application/json; charset=utf-8
7. Standard de documentation des endpoints
7.1. Modèle obligatoire
Chaque endpoint documenté doit suivre exactement ce modèle :

### MÉTHODE /chemin/complet/

**Description courte** : une phrase.

**Description longue** : contexte, cas d'usage, remarques.

**Auth** : JWT / Clé API / Aucune (porte d'entrée)

**Acteurs autorisés** : ADMIN, PARTENAIRE, LIVREUR

**Restriction** : qui exactement peut appeler, sur quelles données.

**Paramètres de requête** : liste des champs (path, query, body).

**Exemple de requête** :
```json
{ ... }

Exemple de réponse succès (200 ou 201) :

json
{ ... }
Exemples d'erreurs :

400 :

json
{ ... }
401 :

json
{ ... }
403 :

json
{ ... }
404 :

json
{ ... }
Codes HTTP possibles : 200, 201, 400, 401, 403, 404

```

## 7.2. Règles de rédaction

1. **Jamais** d'endpoint documenté partiellement.
2. **Toujours** fournir au moins un exemple par code d'erreur mentionné.
3. **Toujours** utiliser des identifiants réalistes (pas de `xxx`, pas de `123`).
4. **Toujours** préciser le mécanisme d'authentification.
5. **Toujours** préciser la restriction d'accès (propriété, portée).
6. **Jamais** documenter un endpoint sans exemple JSON.

## 7.3. Cohérence Swagger / ReDoc / Markdown

Les trois sources doivent être **synchrones** :

- Le code (annotations `@extend_schema`)
- Swagger UI (`/api/docs/`)
- ReDoc (`/api/redoc/`)
- Les fichiers `.md` du projet

En cas de divergence, c'est **le code qui fait foi**, et les `.md` doivent être mis à jour.

---

# 8. Structure du projet

## 8.1. Arborescence globale

```text
mashop_delivery/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   ├── accounts/
│   ├── logistics/
│   ├── courses/
│   ├── partners/
│   └── drivers/
│
├── docs/
│   ├── conventions.md
│   ├── accounts.md
│   ├── logistics.md
│   ├── courses.md
│   ├── partners.md
│   └── drivers.md
│
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```
# Structure détaillée de chaque app

> Section à intégrer dans `docs/conventions.md` — complète la section 8.  
> Chaque app possède **sa propre structure interne**, adaptée à ses responsabilités.  
> Toute app suit la base commune, puis ajoute ses fichiers spécifiques.

---

## Base commune à toutes les apps

Toute app contient **au minimum** les fichiers suivants :

```text
apps/<nom_app>/
├── __init__.py
├── admin.py              # Enregistrement des modèles dans l'admin Django (debug)
├── apps.py               # Configuration de l'app
├── models.py             # Modèles de données
├── serializers.py        # Serializers DRF (entrée / sortie)
├── permissions.py        # Permissions locales DRF
├── views.py              # Vues DRF (ViewSet, APIView, generics)
├── urls.py               # Routes de l'app
├── services.py           # Logique métier (calculs, transitions)
├── exceptions.py         # Exceptions locales à l'app
├── migrations/           # Migrations Django
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    └── test_services.py



App accounts — Personne 1
text
apps/accounts/
├── __init__.py
├── admin.py
├── apps.py
├── models.py                  # User, Partenaire, Livreur, CleAPI
├── enums.py                   # Role, EtatCompte, StatutCleAPI
├── serializers.py             # User, Partenaire, Livreur, CleAPI, Login
├── permissions.py             # EstAdmin, EstPartenaire, EstLivreur
├── authentication.py          # AuthentificationCleAPI (custom DRF)
├── views.py                   # LoginView, PartenaireViewSet, LivreurViewSet
├── urls.py                    # /auth/* et /admin/partenaires/*, /admin/livreurs/*
├── services.py                # creer_partenaire(), generer_cle_api(), revoquer_cle_api(), creer_livreur()
├── exceptions.py              # EmailDejaUtilise, CleAPIInvalide, CompteDesactive
├── migrations/
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_services.py
    └── test_authentication.py
Fichiers spécifiques :

authentication.py → mécanisme d'authentification par clé API (unique à cette app)

enums.py → les énumérations Role, EtatCompte, StatutCleAPI

App logistics — Personne 2
text
apps/logistics/
├── __init__.py
├── admin.py
├── apps.py
├── models.py                  # Zone, Tarif
├── enums.py                   # StatutZone
├── serializers.py             # ZoneSerializer, TarifSerializer, DevisSerializer
├── permissions.py             # EstAdmin, EstPartenaire
├── views.py                   # ZoneViewSet, TarifViewSet, DevisView
├── urls.py                    # /admin/zones/*, /admin/tarifs/*, /partenaire/devis/
├── services.py                # calculer_prix(), creer_zone(), modifier_tarif()
├── selectors.py               # get_zones_actives(), get_tarif_par_couple()
├── exceptions.py              # TarifIntrouvable, ZoneDejaUtilisee
├── migrations/
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_services.py
    └── test_devis.py
Fichiers spécifiques :

selectors.py → fonctions de lecture optimisées (avec cache Redis)

enums.py → StatutZone (ACTIVE / INACTIVE)

App courses — Personne 3 (la plus complexe)
text
apps/courses/
├── __init__.py
├── admin.py
├── apps.py
├── models.py                  # Course, HistoriqueLivraison, Affectation
├── enums.py                   # StatutCourse, StatutAffectation
├── state_machine.py           # TRANSITIONS_AUTORISEES (règles de transition)
├── serializers.py             # CourseSerializer, CourseDetailSerializer, HistoriqueSerializer
├── permissions.py             # EstAdmin
├── views.py                   # DashboardView, CourseAdminViewSet, AssignerCourseView
├── urls.py                    # /admin/dashboard/, /admin/courses/*
├── services.py                # changer_statut(), assigner_course(), zone_est_utilisee()
├── selectors.py               # get_courses_du_jour(), get_stats_dashboard(), get_courses_filtres()
├── exceptions.py              # TransitionInvalide, ConflitConcurrence
├── migrations/
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_services.py
    ├── test_state_machine.py
    └── test_transitions.py
Fichiers spécifiques :

state_machine.py → dictionnaire des transitions autorisées (cœur métier)

selectors.py → agrégations pour le dashboard

services.py → point d'écriture UNIQUE du statut de course

App partners — Personne 4
text
apps/partners/
├── __init__.py
├── admin.py
├── apps.py
├── models.py                  # WebhookLog
├── serializers.py             # CourseCreateSerializer, CourseDetailSerializer, StatutSerializer
├── permissions.py             # EstPartenaire, EstPartenaireOwner
├── views.py                   # PartenaireCourseViewSet, SuivreStatutView
├── urls.py                    # /partenaire/courses/*
├── services.py                # creer_course(), annuler_course(), envoyer_webhook()
├── tasks.py                   # Tâches Celery (envoyer_webhook asynchrone)
├── selectors.py               # get_courses_du_partenaire()
├── exceptions.py              # CourseNonAppartenance, WebhookEchec
├── migrations/
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_services.py
    ├── test_tasks.py
    └── test_webhooks.py
Fichiers spécifiques :

tasks.py → tâches Celery (webhooks, retry, journalisation)

services.py → envoi des webhooks + création de courses

Tests dédiés aux webhooks (test_webhooks.py, test_tasks.py)

App drivers — Personne 5
text
apps/drivers/
├── __init__.py
├── admin.py
├── apps.py
├── serializers.py             # CourseDisponibleSerializer, LivrerSerializer
├── permissions.py             # EstLivreur
├── views.py                   # CoursesDisponiblesView, AccepterCourseView, MarquerRecupereView, LivrerAvecCodeView, CocherPayeView, HistoriqueJourView
├── urls.py                    # /livreur/courses/*
├── services.py                # accepter_course(), marquer_recupere(), livrer_avec_code()
├── selectors.py               # get_courses_disponibles(), get_historique_jour()
├── exceptions.py              # CourseDejaPrise, CodeConfirmationInvalide
├── migrations/                # (aucun modèle propre — voir note ci-dessous)
└── tests/
    ├── __init__.py
    ├── test_views.py
    ├── test_services.py
    └── test_acceptation_concurrente.py
Fichiers spécifiques :

Aucun models.py → cette app n'a pas de modèle propre (utilise ceux de courses et accounts)

selectors.py → filtres sur les courses disponibles

Test dédié à l'acceptation concurrente (test_acceptation_concurrente.py)

Note : drivers n'a pas de models.py ni de migrations/ propres, car tous ses modèles viennent de courses et accounts.

Tableau récapitulatif des fichiers spécifiques
App	Fichiers spécifiques	Modèles propres
accounts	authentication.py, enums.py	User, Partenaire, Livreur, CleAPI
logistics	selectors.py, enums.py	Zone, Tarif
courses	state_machine.py, selectors.py, enums.py	Course, HistoriqueLivraison, Affectation
partners	tasks.py, selectors.py	WebhookLog
drivers	selectors.py	Aucun
Règles de structure
Toute app a la base commune (les 11 fichiers minimum).

Les fichiers spécifiques sont autorisés uniquement s'ils apportent une valeur claire.

Aucune app ne peut ajouter un fichier dans le dossier d'une autre app.

Le nom des fichiers est standardisé : on n'invente pas de nouveaux noms.

models.py est obligatoire sauf pour les apps sans modèle propre (drivers).

tasks.py est obligatoire dès qu'une app utilise Celery (partners uniquement pour l'instant).

selectors.py est recommandé pour les apps avec des lectures complexes (logistics, courses, partners, drivers).