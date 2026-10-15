# MASHOP LIVRAISON — Conventions de code et structure

> Document de référence pour toute l'équipe backend.  
> Complète `architglobale.md` et `accounts.md`.  
> À lire avant d'écrire la première ligne de code.

---

## 1. Structure commune à toutes les apps

```
apps/<nom_app>/
├── __init__.py
├── admin.py              # Enregistrement modèles dans l'admin Django
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
    ├── test_services.py
    └── test_<specific>.py  # Tests spécifiques si besoin
```

### Fichiers spécifiques par app

| App | Fichiers spécifiques | Modèles propres |
|-----|---------------------|-----------------|
| accounts | `authentication.py`, `enums.py` | User, Partenaire, Livreur, CleAPI |
| logistics | `selectors.py`, `enums.py` | Zone, Tarif |
| courses | `state_machine.py`, `selectors.py`, `enums.py` | Course, HistoriqueLivraison, Affectation |
| partners | `tasks.py`, `selectors.py` | WebhookLog |
| drivers | `selectors.py` | Aucun |

---

## 2. Conventions de nommage

### Python (Django/DRF)
- **Modèles** : PascalCase, singulier (`User`, `Partenaire`, `Course`)
- **Champs** : snake_case (`date_creation`, `nom_boutique`)
- **Related_name** : pluriel snake_case (`courses`, `cles_api`)
- **Serializers** : `<Model>Serializer`, `<Model>DetailSerializer`, `<Model>CreateSerializer`
- **Views** : `<Model>ViewSet`, `<Action>View` (`LoginView`, `AccepterCourseView`)
- **Permissions** : `Est<Role>`, `Est<Role>Owner` (`EstAdmin`, `EstPartenaireOwner`)
- **Services** : verbe_infinitif (`creer_partenaire`, `calculer_prix`, `assigner_course`)
- **Selectors** : `get_<pluriel>`, `get_<singulier>_par_<critere>` (`get_courses_du_jour`, `get_tarif_par_couple`)
- **Exceptions** : `<Objet><Action>Exception` ou `<Erreur>Exception` (`EmailDejaUtilise`, `TransitionInvalide`)
- **Enums** : PascalCase, valeurs UPPER_SNAKE_CASE (`Role.ADMIN`, `StatutCourse.EN_COURS`)
- **URLs** : kebab-case (`/api/v1/admin/partenaires/`, `/api/v1/partenaire/courses/`)

### Git
- **Branches** : `feature/<app>-<action>`, `fix/<app>-<bug>`, `chore/<description>`
- **Commits** : `<type>(<app>): <description courte>`
  - Types : `feat`, `fix`, `chore`, `refactor`, `test`, `docs`
  - Exemple : `feat(accounts): ajout endpoint login avec JWT`

---

## 3. Règles de code

### Modèles
- Hériter de `models.Model` (ou `AbstractUser` pour User)
- `db_table` explicite : `'app_modele'`
- `verbose_name` et `verbose_name_plural` en français
- `__str__` lisible
- `ordering` dans Meta si pertinent
- Index sur champs de recherche/filtre fréquents

### Serializers
- Séparer lecture/écriture si champs différents
- `read_only_fields` pour champs auto-générés
- Validation métier dans `validate_<champ>()` ou `validate()`
- Pas de logique métier complexe → aller dans `services.py`

### Views
- ViewSet pour CRUD standard
- APIView pour actions unitaires (login, actions métier)
- `permission_classes` explicites sur chaque vue
- `get_queryset()` pour filtrer selon utilisateur
- `get_serializer_class()` si serializers différents selon action

### Permissions
- Une permission par rôle + une par ownership si besoin
- Message d'erreur explicite en français
- `has_permission` pour accès endpoint, `has_object_permission` pour ownership

### Services
- **Point d'écriture unique** pour la logique métier
- Fonctions pures quand possible (entrées/sorties explicites)
- `@transaction.atomic` pour opérations multi-modèles
- Lever des exceptions métier (pas de `raise ValidationError` brut)
- Pas d'accès direct aux models dans les vues → passer par services

### Selectors
- Fonctions de lecture optimisées (select_related, prefetch_related)
- Cache Redis si lecture fréquente
- Pas d'écriture

### Exceptions
- Hériter de `Exception` (pas `APIException`)
- Message en français dans `__init__`
- Handler global dans `exceptions.py` → format JSON standard

---

## 4. Format de réponse JSON (obligatoire)

### Succès
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

### Erreur
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "identifiant_technique",
    "detail": "Message lisible par un humain"
  }
}
```

### Liste paginée
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
}
```

---

## 5. Documentation des endpoints (obligatoire)

Chaque endpoint dans `views.py` doit avoir un docstring :

```python
class MonViewSet(viewsets.ModelViewSet):
    """
    ### GET /api/v1/xxx/
    
    **Description courte** : Une phrase.
    
    **Description longue** : Contexte, cas d'usage, remarques.
    
    **Auth** : JWT / Clé API / Aucune (porte d'entrée)
    
    **Acteurs autorisés** : ADMIN, PARTENAIRE, LIVREUR
    
    **Restriction** : Qui exactement peut appeler, sur quelles données.
    
    **Paramètres de requête** : Liste des champs (path, query, body).
    
    **Exemple de requête** :
    ```json
    { ... }
    ```
    
    **Exemple de réponse succès (200 ou 201)** :
    ```json
    { ... }
    ```
    
    **Exemples d'erreurs** :
    - 400 : `{ ... }`
    - 401 : `{ ... }`
    - 403 : `{ ... }`
    - 404 : `{ ... }`
    
    **Codes HTTP possibles** : 200, 201, 400, 401, 403, 404
    """
```

---

## 6. Tests

### Structure
- `test_models.py` : création, validation, méthodes modèles
- `test_views.py` : endpoints, permissions, codes HTTP
- `test_services.py` : logique métier, transitions, calculs
- `test_<specific>.py` : cas complexes (concurrence, webhooks, etc.)

### Règles
- **Chaque endpoint testé** : 401 sans token, 403 mauvais rôle, 404 pas propriétaire, 200/201 succès
- **Fixtures** dans `conftest.py` partagé
- `pytest.mark.django_db` sur chaque classe de test
- Données réalistes (pas `test@test.com`, `123`)

---

## 7. Migrations

- `python manage.py makemigrations <app> --name <description_explicite>`
- Jamais modifier une migration appliquée en prod
- Tester sur copie BDD prod avant déploiement
- Une app = ses propres migrations

---

## 8. Variables d'environnement

- **Jamais** de secret en dur
- `.env` en local (gitignoré)
- Secrets manager en prod
- `.env.example` à jour à la racine

---

## 9. Checklist avant merge (PR)

- [ ] `python manage.py check` passe
- [ ] `pytest apps/<mon_app>/` passe (100% endpoints couverts)
- [ ] `ruff check apps/<mon_app>/` passe
- [ ] `black --check apps/<mon_app>/` passe
- [ ] Migrations créées si modèles modifiés
- [ ] Docstrings endpoints à jour
- [ ] `.env.example` mis à jour si nouvelles variables
- [ ] Pas de `print()`, `pdb`, code commenté
- [ ] Commit message conventionnel