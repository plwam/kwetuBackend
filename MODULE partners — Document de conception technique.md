# MODULE partners — Document de conception technique

*Application `apps/partners/` · Personne 4 · Plateforme Mashop Livraison (Goma, RDC)*

> **Objectif du document** : décrire de manière exhaustive le module `partners` avant toute implémentation. Ce document sert de référence pour l'équipe : tout développeur qui touche à `partners`, ou qui doit appeler `envoyer_webhook()`, doit d'abord lire ce fichier.

## Partie 1 — Compréhension du module

### 1.1. Vue d'ensemble

Le module `partners` est le **côté partenaire du backend**. Un partenaire est une boutique (Kivu Shop, Mama Mode, Goma Tech) qui confie ses colis à la plateforme. Le module remplit deux rôles :

1. **Exposer l'API partenaire** : cinq endpoints, sous le préfixe `/api/v1/partenaire/`, authentifiés par clé API, permettant de créer une course, de lister ses courses, d'en consulter le détail, de l'annuler et d'en suivre le statut.
2. **Envoyer les webhooks sortants** : à chaque changement de statut d'une course, le module envoie une requête POST à l'`url_webhook` du partenaire et journalise le résultat dans `WebhookLog`.

| Élément | Valeur |
| --- | --- |
| Chemin | `apps/partners/` |
| Modèle propre | `WebhookLog` |
| Authentification | Clé API (fournie par `accounts`) |
| Tâche asynchrone | `envoyer_webhook()` (Celery, 3 relances) |
| Cas d'utilisation couverts | CréerCourse, ConsulterDétailCourse, AnnulerCourse, SuivreStatutCourse, RecevoirNotificationWebhook |

### 1.2. Position dans l'architecture

```
            accounts ──────────────┐
   (CleAPIAuthentication,          │ utilise
        IsPartenaire)              ▼
                              ┌──────────┐
   logistics ───────────────► │ partners │ ◄──────── courses
   (calculer_prix)  utilise   └──────────┘   courses appelle
                                   ▲         partners.envoyer_webhook()
                                   │         partners lit Course et appelle
                                   │         courses.changer_statut()
                              Partenaires
                           (clé API, HTTPS)
```

| App | Sens | Ce qui circule |
| --- | --- | --- |
| `accounts` | partners → accounts | `CleAPIAuthentication`, `IsPartenaire` |
| `logistics` | partners → logistics | `calculer_prix(zone_depart, zone_arrivee)` |
| `courses` | partners → courses | modèle `Course`, service `changer_statut()` |
| `courses` | courses → partners | appel de `envoyer_webhook()` à chaque transition |

La relation avec `courses` est **bidirectionnelle**. C'est le seul point sensible du module : elle impose des imports locaux (voir 4.4).

### 1.3. Vocabulaire métier

| Terme | Définition |
| --- | --- |
| **Partenaire** | Boutique cliente de la plateforme. Possède un compte utilisateur, une clé API et, optionnellement, une `url_webhook`. |
| **Course** | Demande de livraison d'un colis d'une zone de départ vers une zone d'arrivée, avec un prix et un statut. |
| **Statut** | État d'une course : `creee`, `acceptee`, `recuperee`, `livree`, `annulee`. |
| **Clé API** | Secret transmis dans l'en-tête `Authorization` qui identifie un partenaire. Générée et vérifiée par `accounts`. |
| **Webhook** | Notification HTTP POST envoyée par la plateforme au système du partenaire lors d'un changement de statut. |
| **WebhookLog** | Trace d'une tentative d'envoi de webhook (URL, contenu, code HTTP, succès). |
| **Propriétaire** | Le partenaire qui a créé la course. Seul lui peut la consulter ou l'annuler. |
| **Devis** | Prix calculé par le serveur d'après la grille tarifaire (zone de départ, zone d'arrivée). |

### 1.4. Périmètre

**Ce que le module fait**

- Créer une course pour le compte du partenaire authentifié, avec calcul du prix côté serveur.
- Lister, consulter et suivre les courses du partenaire.
- Annuler une course (statuts `creee` ou `acceptee` uniquement).
- Envoyer les webhooks, relancer en cas d'échec, journaliser chaque tentative.

**Ce que le module ne fait pas**

| Hors périmètre | Responsable |
| --- | --- |
| Authentifier la clé API, générer ou révoquer une clé | `accounts` |
| Définir le modèle `Course` et les transitions de statut | `courses` |
| Calculer les tarifs, gérer zones et grille | `logistics` |
| Gérer les partenaires (créer, désactiver) côté administrateur | `accounts` (`/admin/partenaires/`) |
| Actions livreur (accepter, récupérer, livrer) | `courses` |

### 1.5. Principe fondateur

Deux principes gouvernent tout le module :

1. **Aucun endpoint public.** Chaque endpoint exige une clé API valide et un rôle partenaire. Sans clé valide, la réponse est 401.
2. **Échec webhook ≠ échec du changement de statut** (exigence « Fiabilité » du rapport). Le webhook est une conséquence d'un changement de statut ; il ne peut jamais l'empêcher ni l'annuler.

## Partie 2 — Fonctionnement interne

### 2.1. Modèle conceptuel de données

Le module ne possède qu'**une entité**, `WebhookLog`. Il manipule trois entités appartenant à d'autres apps.

| Entité | App propriétaire | Rôle pour `partners` |
| --- | --- | --- |
| **Partenaire** | `accounts` | Identité de l'appelant ; porte `url_webhook` |
| **Course** | `courses` | Objet principal des endpoints |
| **HistoriqueCourse** | `courses` | Affiché dans le détail et le suivi |
| **WebhookLog** | `partners` | Trace des envois de webhooks |

**WebhookLog**

| Champ | Type conceptuel | Remarque |
| --- | --- | --- |
| `course` | Référence vers Course | Suppression en cascade |
| `url` | URL | URL appelée au moment de l'envoi |
| `payload` | Document JSON | Contenu exact envoyé |
| `statut_http` | Entier, facultatif | Vide si aucune réponse (erreur réseau) |
| `succes` | Booléen | Vrai si la réponse est de type 2xx |
| `date_envoi` | Date et heure | Renseignée automatiquement |

**Relations** : un Partenaire possède 0..N Courses ; une Course possède 0..N WebhookLog et 0..N HistoriqueCourse. Un WebhookLog est créé par **tentative** : une course avec trois échecs successifs produit trois lignes.

### 2.2. Cycle de vie d'une course côté partenaire

```
 creee ──► acceptee ──► recuperee ──► livree
   │          │
   └──────────┴──► annulee
```

| Statut | Qui y fait passer | Le partenaire peut-il annuler ? |
| --- | --- | --- |
| `creee` | Partenaire (création) | Oui |
| `acceptee` | Livreur ou administrateur | Oui |
| `recuperee` | Livreur | Non (409) |
| `livree` | Livreur | Non (409) |
| `annulee` | Partenaire | Non (déjà annulée, 409) |

Le partenaire ne modifie **jamais** un statut directement : il crée (statut initial `creee`) ou demande l'annulation, qui passe par `courses.changer_statut()`. Chaque transition déclenche un webhook.

### 2.3. Mécanisme d'envoi des webhooks

```
changer_statut()  ──(transaction validée)──►  envoyer_webhook.delay()
                                                   │ file Celery
                                                   ▼
                                         POST url_webhook (timeout 5 s)
                                           │              │
                                         2xx           erreur / timeout
                                           │              │
                                   WebhookLog OK    WebhookLog échec
                                                          │
                                              relance dans 10 s (max 3)
```

| Paramètre | Valeur |
| --- | --- |
| Contenu envoyé | `reference`, `ancien_statut`, `nouveau_statut` |
| Délai d'attente (timeout) | 5 secondes |
| Nombre maximal de relances | 3 |
| Délai entre relances | 10 secondes |
| URL vide | La tâche s'arrête sans rien envoyer ni journaliser |

**Point clé** : la tâche est lancée **après validation de la transaction** (`transaction.on_commit`) et **jamais attendue**. Une erreur réseau reste donc confinée au worker Celery.

**Précision sur le succès** : `response.ok` est vrai pour tout code inférieur à 400. Un code 500 renvoyé par le partenaire n'est donc pas une exception : il est journalisé avec `succes = False`, mais il ne déclenche pas de relance. Seules les exceptions réseau déclenchent la relance. À valider avec l'équipe si les codes 5xx doivent aussi relancer.

### 2.4. Gestion des rôles et permissions

| Classe | App | Rôle |
| --- | --- | --- |
| `CleAPIAuthentication` | `accounts` | Identifie le partenaire d'après la clé API ; sinon 401 |
| `IsPartenaire` | `accounts` | Vérifie que l'utilisateur authentifié a un profil partenaire |
| `IsPartenaireOwner` | `partners` (locale) | Vérifie qu'une course appartient au partenaire ; sinon 403 |

Ordre d'évaluation sur chaque requête : **authentification → rôle → propriété de l'objet**.

### 2.5. Gestion de l'URL de webhook

| Aspect | Règle |
| --- | --- |
| Configuration | Par l'administrateur, à la création ou modification du partenaire (`accounts`) |
| Facultative | Sans `url_webhook`, aucun webhook n'est envoyé |
| Modification | Prise en compte à partir de l'envoi suivant ; les anciens `WebhookLog` conservent l'URL utilisée à l'époque |
| Suivi | Les `WebhookLog` sont consultables par l'administrateur, pas exposés dans l'API partenaire |

## Partie 3 — Interfaces exposées (API)

### 3.1. Endpoints partenaire — `/api/v1/partenaire/*`

| Méthode | URL | Cas d'utilisation | Succès |
| --- | --- | --- | --- |
| POST | `/api/v1/partenaire/courses/` | CréerCourse | 201 |
| GET | `/api/v1/partenaire/courses/` | Lister ses courses | 200 |
| GET | `/api/v1/partenaire/courses/{id}/` | ConsulterDétailCourse | 200 |
| POST | `/api/v1/partenaire/courses/{id}/annuler/` | AnnulerCourse | 200 |
| GET | `/api/v1/partenaire/courses/{id}/statut/` | SuivreStatutCourse | 200 |

Tous utilisent l'en-tête `Authorization` (clé API). Le format exact du préfixe de l'en-tête est défini par `accounts`.

### 3.2. Webhook sortant (interface appelée par la plateforme)

Ce n'est pas un endpoint de la plateforme mais un **contrat** que le partenaire doit respecter côté serveur :

| Élément | Valeur |
| --- | --- |
| Méthode | POST |
| URL | `url_webhook` du partenaire |
| Corps | JSON (voir 3.3) |
| Réponse attendue | Code 2xx en moins de 5 secondes |

Le partenaire doit traiter chaque notification de manière **idempotente** : une relance peut renvoyer le même événement.

### 3.3. Contrats d'entrée/sortie

**Création d'une course** : `POST /api/v1/partenaire/courses/`

Requête :

```json
{
  "zone_depart": 1,
  "zone_arrivee": 3,
  "destinataire_nom": "Amani K.",
  "destinataire_tel": "+243970000000",
  "description_colis": "Robe en carton"
}
```

Réponse 201 :

```json
{
  "id": 42,
  "reference": "GM-1042",
  "zone_depart": 1,
  "zone_arrivee": 3,
  "destinataire_nom": "Amani K.",
  "destinataire_tel": "+243970000000",
  "description_colis": "Robe en carton",
  "prix": "4.00",
  "statut": "creee",
  "paye": false,
  "date_creation": "2026-10-14T08:12:00Z",
  "historique": []
}
```

Le partenaire **ne peut pas** fournir `prix`, `statut`, `reference` ni `paye` : ces champs sont ignorés ou calculés par le serveur.

**Suivi du statut** : `GET .../courses/42/statut/`

```json
{
  "reference": "GM-1042",
  "statut": "acceptee",
  "historique": [
    {
      "ancien_statut": "creee",
      "nouveau_statut": "acceptee",
      "date": "2026-10-14T08:20:00Z"
    }
  ]
}
```

**Contenu du webhook** :

```json
{
  "reference": "GM-1042",
  "ancien_statut": "creee",
  "nouveau_statut": "acceptee"
}
```

**Liste** : `GET .../courses/` renvoie un tableau de courses au format du détail, limitées aux courses du partenaire authentifié.

### 3.4. Codes d'erreur spécifiques au module

| Code | Situation | Exemple de corps |
| --- | --- | --- |
| 400 | Données invalides (champ manquant, zone inexistante) | `{"zone_depart": ["Ce champ est obligatoire."]}` |
| 400 | Aucun tarif pour le couple de zones | `{"zones": "Aucun tarif pour ce couple de zones."}` |
| 401 | Clé API absente, invalide ou expirée | `{"detail": "Clé API invalide."}` |
| 403 | Course appartenant à un autre partenaire, ou compte non partenaire | `{"detail": "Vous n'avez pas la permission d'effectuer cette action."}` |
| 404 | Course inexistante | `{"detail": "Introuvable."}` |
| 409 | Annulation impossible (statut `recuperee`, `livree` ou `annulee`) | `{"detail": "Cette course ne peut plus être annulée."}` |

### 3.5. Vue d'ensemble de la sécurité des endpoints

| Endpoint | Clé API | Rôle partenaire | Propriété vérifiée |
| --- | --- | --- | --- |
| POST courses/ | Oui | Oui | Sans objet (création) |
| GET courses/ | Oui | Oui | Par filtre du queryset |
| GET courses/{id}/ | Oui | Oui | Oui (403) |
| POST courses/{id}/annuler/ | Oui | Oui | Oui (403) |
| GET courses/{id}/statut/ | Oui | Oui | Oui (403) |

### 3.6. Convention d'écriture des exemples JSON

- Identifiants : entiers. Références métier : `GM-xxxx`.
- Prix : **chaîne décimale** en USD (`"4.00"`), jamais un nombre flottant.
- Dates : ISO 8601 en UTC.
- Statuts : minuscules, sans accent (`creee`, `acceptee`, `recuperee`, `livree`, `annulee`).
- Erreurs : clé `detail` (message en français) ou dictionnaire champ → liste de messages.
- Numéros de téléphone : format international (`+243…`).

## Partie 4 — Communication avec les autres modules

### 4.1. Ce que `partners` expose aux autres apps

| Élément | Utilisé par | Usage |
| --- | --- | --- |
| `services.envoyer_webhook(course_id, ancien, nouveau)` | `courses` | Notifier le partenaire après chaque transition |
| `models.WebhookLog` | Administration (`accounts`, tableau de bord) | Consulter l'historique des envois |

L'appel se fait toujours par `.delay()`, jamais en appel direct synchrone.

### 4.2. Ce que `partners` attend des autres apps

| De | Attente | Si absent |
| --- | --- | --- |
| `accounts` | `CleAPIAuthentication` renvoie un utilisateur disposant de `.partenaire` ; `IsPartenaire` | Aucun accès possible |
| `courses` | `Course` avec `partenaire`, `reference`, `prix`, `statut`, `historique` ; `changer_statut(course_id, nouveau)` | Création et annulation impossibles |
| `courses` | Génération de `reference` (et du code de confirmation) par le modèle | Courses sans référence |
| `logistics` | `calculer_prix()` renvoie un prix ou `None` si aucun tarif | Création impossible |

### 4.3. Diagramme de flux des échanges inter-apps

**Création d'une course**

```
Partenaire ─POST─► partners.views ─► accounts (clé API, rôle)
                        │
                        ├─► logistics.calculer_prix()
                        └─► courses.Course.create()   → 201
```

**Annulation avec notification**

```
Partenaire ─POST annuler─► partners.views ─► IsPartenaireOwner
                              │
                              └─► courses.changer_statut(id, annulee)
                                      ├─► met à jour Course + historique
                                      └─► (après commit) partners.envoyer_webhook.delay()
                                                   └─► POST url_webhook ─► WebhookLog
```

### 4.4. Règles d'import à respecter

| Qui | Peut importer | Ne doit pas importer |
| --- | --- | --- |
| `partners` | `accounts` (authentification, permissions), en tête de fichier | Les vues ou serializers des autres apps |
| `partners` | `courses` et `logistics` **à l'intérieur des fonctions** | `courses` en tête de `services.py` (import circulaire) |
| `courses` | `partners.services.envoyer_webhook` (à l'intérieur de `changer_statut`) | `partners.models` |
| `accounts` | Rien de `partners` | Tout (dépendance unidirectionnelle) |

**Pourquoi** : `courses` importe `partners` pour le webhook et `partners` importe `courses` pour le modèle `Course`. Deux imports en tête de fichier se bloqueraient mutuellement au démarrage de Django.

### 4.5. Ce que `partners` n'expose jamais

- Les clés API (ni en clair, ni sous forme hachée).
- Les `WebhookLog` aux partenaires.
- Les courses, historiques ou tarifs d'un autre partenaire.
- Le code de confirmation de livraison (réservé au destinataire et au livreur).
- Les informations du livreur (téléphone, position) : le partenaire ne voit que le statut.

### 4.6. Endpoints internes vs points d'entrée

| Type | Exemples | Règle |
| --- | --- | --- |
| Point d'entrée externe (partenaire) | `/api/v1/partenaire/*` | Clé API obligatoire |
| Appel interne (Python) | `envoyer_webhook()`, `creer_course()`, `annuler_course()` | Jamais exposé en HTTP |
| Appel sortant | POST vers `url_webhook` | Initié par la plateforme, via Celery |

## Partie 5 — Restriction d'accès aux données

### 5.1. Principe général

**« Chaque partenaire ne voit et ne modifie que ce qui lui appartient. »** Un partenaire n'a aucune visibilité sur les autres partenaires, ni sur l'administration, ni sur les livreurs.

### 5.2. Matrice d'accès aux données

| Donnée | Partenaire (propriétaire) | Autre partenaire | Livreur / Admin |
| --- | --- | --- | --- |
| Ses courses (liste) | Lecture | Aucune | Via leurs propres endpoints |
| Détail d'une course | Lecture | 403 | Via leurs propres endpoints |
| Historique des statuts | Lecture | 403 | Via leurs propres endpoints |
| Annulation | Si `creee` ou `acceptee` | 403 | Hors module |
| Prix | Lecture seule | 403 | Hors module |
| `WebhookLog` | Aucun accès | Aucun accès | Admin uniquement |
| Clé API | Aucun accès via ce module | Aucun accès | `accounts` |

### 5.3. Filtrage obligatoire par rôle

- **Liste** : le queryset est filtré sur `request.user.partenaire`.
- **Détail, statut, annulation** : la course est chargée, puis `IsPartenaireOwner` compare `course.partenaire_id` au partenaire authentifié.
- Un nouveau endpoint ne peut être ajouté qu'avec ces deux protections.

### 5.4. Vérification côté serveur

Le serveur ne fait **jamais** confiance aux données envoyées par le client :

- Le partenaire d'une course est déduit de la clé API, jamais d'un champ du corps de la requête.
- Le prix et le statut sont ignorés s'ils sont envoyés.
- L'identifiant `{id}` de l'URL est toujours revérifié contre le propriétaire.

### 5.5. Cas particuliers

| Catégorie | Situation dans `partners` |
| --- | --- |
| Public | Aucun endpoint public |
| Authentifié (clé API) | Les 5 endpoints, restreints au propriétaire |
| Administrateur | N'utilise pas ce module : il dispose de `/admin/*` |
| Partenaire désactivé | Clé refusée par `accounts` : 401 ou 403 selon l'implémentation |

### 5.6. Erreurs à renvoyer

| Code | Signification | Déclencheur |
| --- | --- | --- |
| **401** | Je ne sais pas qui vous êtes | Clé API absente, invalide, expirée |
| **403** | Je sais qui vous êtes, mais ce n'est pas à vous | Course d'un autre partenaire |
| **404** | Cela n'existe pas | Course inexistante |

**Compromis à connaître** : distinguer 404 et 403 révèle à un partenaire qu'un identifiant de course existe chez un autre. C'est la règle du cahier des charges (« course d'un autre partenaire → 403 »). Les identifiants étant séquentiels, un partenaire peut les énumérer. Pour limiter ce risque, on peut renvoyer 404 dans les deux cas ; cette décision doit être prise en équipe avant de coder.

### 5.7. Exemples concrets de tentatives refusées

| Tentative | Résultat |
| --- | --- |
| Appel sans en-tête `Authorization` | 401 |
| Clé API révoquée ou inventée | 401 |
| `GET /courses/42/` alors que la course 42 est à Mama Mode et que l'appelant est Kivu Shop | 403 |
| `POST /courses/42/annuler/` sur la course d'un autre | 403 |
| `GET /courses/99999/` inexistante | 404 |
| Annuler une course `livree` | 409 |
| Envoyer `"prix": "0.01"` à la création | Champ ignoré, prix calculé par le serveur |
| Utiliser un jeton livreur ou administrateur sur ces endpoints | 403 |

### 5.8. Distinction authentification / autorisation / restriction

| Notion | Question | Où dans le module |
| --- | --- | --- |
| **Authentification** | Qui êtes-vous ? | `CleAPIAuthentication` (accounts) |
| **Autorisation** | Avez-vous le droit d'utiliser cette fonction ? | `IsPartenaire` (accounts) |
| **Restriction** | Avez-vous le droit de toucher *cet objet* ? | `IsPartenaireOwner` et filtre du queryset (partners) |

### 5.9. Règle du « deny by default »

- Chaque vue déclare **explicitement** `authentication_classes` et `permission_classes`.
- Sans déclaration claire, l'accès est refusé.
- Toute nouvelle action sur `PartenaireCourseViewSet` hérite de ces protections ; aucune action n'est ouverte par omission.

## Partie 6 — Règles métier et contraintes

### 6.1. Règles de sécurité

- Authentification par clé API obligatoire sur tous les endpoints.
- Les clés ne sont jamais stockées en clair (hachage, géré par `accounts`).
- Le prix est **toujours** calculé par le serveur via `logistics.calculer_prix()`.
- Les erreurs ne divulguent pas d'informations internes (pas de trace Python dans la réponse).
- Le webhook ne contient aucune donnée sensible : pas de code de confirmation, pas de données du livreur.
- Recommandation hors cahier des charges : signer les webhooks (signature HMAC dans un en-tête) pour que le partenaire puisse vérifier l'origine. À décider.

### 6.2. Règles d'intégrité

| Règle | Mise en œuvre |
| --- | --- |
| Un partenaire ne voit que ses courses | Filtre du queryset + `IsPartenaireOwner` |
| Annulation uniquement si `creee` ou `acceptee` | `annuler_course()` ; sinon 409 |
| Une annulation passe par `changer_statut()` | Transition validée, historique écrit, webhook déclenché |
| Pas de course sans tarif | `calculer_prix()` renvoie `None` → 400 |
| Création toujours au statut `creee` | Fixé par `creer_course()`, non modifiable par le client |
| Échec webhook ≠ échec du changement de statut | `on_commit` + tâche asynchrone |

### 6.3. Règles de cycle de vie

- **Une course n'est jamais supprimée** par le partenaire : elle est annulée (statut `annulee`) et reste dans l'historique.
- Les `WebhookLog` sont supprimés uniquement avec leur course (cascade). Aucune suppression manuelle via l'API.
- Un partenaire désactivé ne peut plus utiliser l'API, mais ses courses et journaux sont conservés.
- Politique de conservation des `WebhookLog` (purge après N mois) : à définir.

### 6.4. Cas limites et pièges à éviter

| Piège | Conséquence | Parade |
| --- | --- | --- |
| Importer `Course` en tête de `services.py` | Import circulaire, Django ne démarre pas | Imports locaux dans les fonctions |
| Lancer `envoyer_webhook` **avant** le commit | Le partenaire reçoit un statut qui sera annulé par un rollback | `transaction.on_commit` |
| Appeler `envoyer_webhook()` sans `.delay()` | La requête HTTP bloque la réponse | Toujours `.delay()` |
| Filtrer le queryset partout | Un autre partenaire reçoit 404 au lieu de 403 | Filtrer seulement la liste ; `IsPartenaireOwner` pour le reste |
| Webhook relancé trois fois | Le partenaire reçoit le même événement plusieurs fois | Documenter l'idempotence |
| Réponse 5xx du partenaire | Journalisée en échec, sans relance | Décision d'équipe (voir 2.3) |
| Partenaire sans `url_webhook` | Aucun envoi, aucun log | Comportement normal |
| Deux annulations simultanées | Double transition | `select_for_update` dans `changer_statut()` (courses) |
| Annuler une course `recuperee` | Colis déjà en route | 409 |
| Worker Celery arrêté | Webhooks en attente | Surveiller la file ; relancer le worker |
| `CELERY_TASK_ALWAYS_EAGER = True` en production | Envois synchrones | Réservé au développement et aux tests |

## Partie 7 — Stratégie de tests

### 7.1. Ce qu'il faut tester en priorité

1. **Cloisonnement** : un partenaire ne peut jamais lire ni annuler la course d'un autre.
2. **Fiabilité du webhook** : un échec n'altère pas le statut de la course.
3. **Calcul du prix** : le prix vient du serveur, quoi que le client envoie.
4. **Règle d'annulation** : seuls `creee` et `acceptee` sont annulables.
5. **Codes d'erreur** : 400, 401, 403, 404, 409 renvoyés dans les bons cas.

### 7.2. Scénarios critiques

| # | Scénario | Résultat attendu |
| --- | --- | --- |
| 1 | Création avec zones valides et tarif existant | 201, prix égal au tarif, statut `creee` |
| 2 | Création avec un prix envoyé dans le corps | Prix du serveur, champ ignoré |
| 3 | Création sans tarif pour le couple de zones | 400 |
| 4 | Création avec champ obligatoire manquant | 400 |
| 5 | Appel sans clé API | 401 |
| 6 | Appel avec clé révoquée | 401 |
| 7 | Liste : deux partenaires ayant chacun des courses | Chacun ne voit que les siennes |
| 8 | Détail de sa propre course | 200, historique inclus |
| 9 | Détail d'une course d'un autre partenaire | 403 |
| 10 | Détail d'une course inexistante | 404 |
| 11 | Annulation d'une course `creee` | 200, statut `annulee`, historique écrit, webhook envoyé |
| 12 | Annulation d'une course `acceptee` | 200 |
| 13 | Annulation d'une course `recuperee`, `livree` ou `annulee` | 409, statut inchangé |
| 14 | Annulation de la course d'un autre partenaire | 403 |
| 15 | Suivi du statut de sa propre course | 200, statut et historique |
| 16 | Webhook : réponse 200 du partenaire | `WebhookLog` avec `succes = True` et `statut_http = 200` |
| 17 | Webhook : exception réseau | `WebhookLog` en échec, relance planifiée, statut de la course inchangé |
| 18 | Webhook : trois relances épuisées | Trois `WebhookLog` en échec, aucune exception remontée au changement de statut |
| 19 | Webhook : partenaire sans `url_webhook` | Aucun envoi, aucun log |
| 20 | Webhook : rollback de la transaction | Aucun webhook envoyé |

**Méthode** : tests d'API avec le client de test de DRF ; `requests.post` simulé avec `unittest.mock.patch` ; `CELERY_TASK_ALWAYS_EAGER = True` dans les réglages de test.

**Critère de livraison** : les scénarios 7, 9, 13 et 17 doivent passer avant toute intégration avec les autres apps.
