# Mashop Livraison - Backend Django

## Stack technique
- **Django 5.x** + **Django REST Framework**
- **SimpleJWT** pour l'authentification JWT
- **Clé API** personnalisée pour partenaires
- **PostgreSQL** (prod) / **SQLite** (dev)
- **Redis** + **Celery** pour cache et tâches asynchrones
- **drf-spectacular** pour documentation API (Swagger/ReDoc)

## Installation

### Prérequis
- Python 3.11+
- PostgreSQL 15+ (production)
- Redis 7+

### Développement local

```bash
# 1. Cloner le repo
git clone <repo-url>
cd mashop-delivery

# 2. Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 5. Appliquer les migrations
python manage.py migrate

# 6. Créer un superutilisateur (premier ADMIN)
python manage.py createsuperuser

# 7. Lancer le serveur
python manage.py runserver
```

### Lancer les tests
```bash
pytest apps/accounts/
pytest apps/logistics/
pytest apps/courses/
pytest apps/partners/
pytest apps/drivers/
# Ou tout
pytest
```

### Linter / Formatter
```bash
ruff check apps/
black --check apps/
# Pour corriger
ruff check --fix apps/
black apps/
```

## Structure du projet
```
mashop-delivery/
├── config/                 # Configuration Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py
├── apps/                   # Applications métier
│   ├── accounts/           # Authentification, utilisateurs, rôles
│   ├── logistics/          # Zones, tarifs
│   ├── courses/            # Courses, affectations, statuts
│   ├── partners/           # Interface partenaire (courses, webhooks)
│   └── drivers/            # Interface livreur (courses, livraison)
├── docs/                   # Documentation
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
├── pytest.ini
└── README.md
```

## Documentation API
- **Swagger UI** : `/api/docs/` (accessible aux ADMIN uniquement en prod)
- **ReDoc** : `/api/redoc/`
- **Schéma OpenAPI** : `/api/schema/`

## Workflow Git
Voir `docs/Guide GitHub et workflow Git.md`

## Rôles utilisateurs
- **ADMIN** : Gestion globale (création partenaires/livreurs, clés API)
- **PARTENAIRE** : Création courses, suivi, webhooks
- **LIVREUR** : Acceptation courses, livraison, paiement

## Authentification
- **JWT** : Tous les acteurs (access 30min, refresh 7j)
- **Clé API** : Partenaires uniquement (header `X-API-Key`)

## Déploiement production
```bash
# Variables d'environnement requises
export DJANGO_SETTINGS_MODULE=config.settings.prod
export DJANGO_SECRET_KEY=...
export DATABASE_URL=postgres://...
export REDIS_URL=redis://...
export JWT_SIGNING_KEY=...
export ALLOWED_HOSTS=api.mashop.cd
export CORS_ALLOWED_ORIGINS=https://mashop.cd

# Collecte static files
python manage.py collectstatic --noinput

# Gunicorn + Nginx (voir config prod)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Équipe
- **Personne 1** : `accounts` (auth, users, roles, API keys)
- **Personne 2** : `logistics` (zones, tarifs, devis)
- **Personne 3** : `courses` (courses, affectations, state machine)
- **Personne 4** : `partners` (interface partenaire, webhooks)
- **Personne 5** : `drivers` (interface livreur, livraison)