# MASHOP LIVRAISON — Consignes globales de l'application

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
