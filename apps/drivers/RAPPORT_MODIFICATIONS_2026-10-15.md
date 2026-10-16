# Rapport des modifications — application `drivers`

**Date :** 15 octobre 2026  
**Périmètre :** application `apps/drivers` du backend KwetuBest  
**Base API :** `/api/v1/livreur/`

## Synthèse

L’application `drivers` fournit désormais les principaux parcours API du livreur : consultation des courses disponibles et en cours, acceptation d’une course, récupération du colis, confirmation de livraison par code, enregistrement du paiement et consultation de l’historique journalier.

Les opérations s’appuient sur les modèles de courses et d’affectations existants. L’application `drivers` ne définit pas de modèle de données propre. Les routes ont été remplacées : l’ancienne route provisoire `courses/` qui retournait simplement `OK` laisse place à sept routes dédiées.

## Fonctionnalités implémentées

### Authentification et autorisations

- Les vues utilisent l’authentification JWT.
- L’accès est réservé à un compte ayant le rôle `LIVREUR`, un profil livreur associé et un profil actif.
- Le profil effectuant l’action est déduit de l’utilisateur authentifié ; il n’est pas choisi à partir des données envoyées par le client.
- Les erreurs d’authentification et d’autorisation sont renvoyées dans une enveloppe API cohérente.

### Consultation des courses

- **Courses disponibles** : courses créées et sans livreur assigné, triées de la plus ancienne à la plus récente. Les données exposées avant acceptation sont limitées.
- **Courses en cours** : courses acceptées ou récupérées par le livreur connecté uniquement. Les informations de partenaire et le téléphone du destinataire sont alors disponibles.
- **Historique du jour** : courses livrées pendant la journée locale en cours, triées de la plus récente à la plus ancienne. La réponse comprend la date, le nombre de livraisons et leur montant total en USD.
- Les trois listes sont paginées : 20 éléments par défaut, paramètre `page_size` plafonné à 100.
- Le résumé journalier porte sur toutes les livraisons de la journée, et non uniquement sur la page courante.

### Actions de livraison

- **Accepter une course** : l’affectation est créée et le statut de la course est modifié. Le verrouillage de la course et la gestion du conflit d’affectation empêchent qu’une course déjà prise soit acceptée une seconde fois ; le conflit est signalé par une réponse HTTP 409.
- **Marquer le colis récupéré** : possible uniquement pour une course affectée au livreur connecté et déjà acceptée.
- **Confirmer la livraison** : le livreur transmet un code obligatoire, non vide, limité à 64 caractères. La livraison n’est possible qu’après récupération du colis. La comparaison du code utilise `hmac.compare_digest`.
- **Enregistrer le paiement** : possible pour une course récupérée ou livrée. L’action est idempotente : la répéter ne remet pas le paiement à zéro et ne crée pas une seconde opération de marquage.
- Après confirmation, une date de livraison est renseignée si le service de changement de statut n’en a pas déjà attribué une.

### Protection contre les essais répétés et confidentialité

- Par défaut, trois codes erronés bloquent temporairement la confirmation pendant 900 secondes. Les valeurs peuvent être remplacées via `DRIVERS_MAX_TENTATIVES_CODE` et `DRIVERS_DUREE_BLOCAGE_SECONDES` ; une limite maximale inférieure ou égale à zéro désactive le comptage.
- Le compteur est conservé dans le cache et associé à la course et au livreur. Un code correct réinitialise le compteur.
- Le code de confirmation n’est inclus dans aucun sérialiseur de réponse.
- Les réponses destinées aux courses disponibles n’exposent ni le téléphone du destinataire ni le nom du partenaire ; les sérialiseurs de l’historique omettent également le téléphone.

## Routes ajoutées ou remplacées

| Méthode | Route | Fonction |
|---|---|---|
| `GET` | `/courses/disponibles/` | Lister les courses à prendre |
| `GET` | `/courses/en-cours/` | Lister les courses du livreur en cours |
| `POST` | `/courses/{id}/accepter/` | Accepter une course |
| `POST` | `/courses/{id}/recuperer/` | Signaler la récupération du colis |
| `POST` | `/courses/{id}/livrer/` | Confirmer la livraison avec `{"code": "..."}` |
| `POST` | `/courses/{id}/payer/` | Marquer le paiement comme encaissé |
| `GET` | `/historique/` | Consulter les livraisons du jour et leur résumé |

Toutes ces routes sont sous le préfixe `/api/v1/livreur/`.

## Format des réponses et erreurs

Les réponses de succès utilisent la structure `{"success": true, "data": ..., "error": null}`. Les réponses d’erreur utilisent `{"success": false, "data": null, "error": {"code": ..., "detail": ...}}`.

Les erreurs couvrent notamment l’absence ou l’invalidité du jeton, l’accès refusé ou le compte désactivé, une course introuvable ou non assignée, les transitions de statut invalides, les conflits d’acceptation, les données de code invalides, le code incorrect, le blocage temporaire et le paiement impossible.

## Fichiers concernés aujourd’hui

Les fichiers ci-dessous sont présents dans les changements locaux datés du 15 octobre 2026. Le statut Git observé au moment de la rédaction montre ces nouveaux modules comme non suivis et `urls.py` comme modifié ; aucun commit ne contient encore ces changements.

- `apps/drivers/apps.py` : configuration Django de l’application.
- `apps/drivers/exceptions.py` : erreurs métier dédiées et codes/statuts HTTP associés.
- `apps/drivers/permissions.py` : contrôle du rôle, du profil et de l’activation du livreur.
- `apps/drivers/serializers.py` : formats de sortie des courses et validation du code de livraison.
- `apps/drivers/services.py` : requêtes de consultation, règles métier, transitions, affectation, cache des tentatives et paiement.
- `apps/drivers/views.py` : vues API, pagination et conversion des exceptions vers le format de réponse commun.
- `apps/drivers/urls.py` : remplacement de la route provisoire par les sept routes fonctionnelles décrites ci-dessus.
- `apps/drivers/tests.py/outils.py` : fabriques de données et client de test authentifié.
- `apps/drivers/tests.py/test_views.py` : tests d’accès, listes, pagination, parcours de bout en bout, règles d’affectation, codes erronés, paiement et non-exposition du code.
- `apps/drivers/tests.py/test_models.py` : test vérifiant que l’application ne définit pas de modèles propres.
- `apps/drivers/__init__.py`, `apps/drivers/migrations/__init__.py` et `apps/drivers/tests.py/__init__.py` : fichiers d’initialisation.

`admin.py`, `models.py` et `tests.py/test_services.py` sont présents mais vides ; aucune fonctionnalité spécifique n’y est implémentée dans l’état observé.

## Tests et intégration

Les tests ajoutés couvrent les refus d’accès sans JWT, avec un rôle autre que livreur ou avec un compte désactivé ; les réponses paginées et les champs exposés ; le parcours complet jusqu’à l’historique ; les erreurs d’affectation et de transition ; la limite de codes erronés ; l’idempotence du paiement ; ainsi que l’absence du code de confirmation dans les réponses.

L’application est enregistrée dans la configuration Django et ses routes sont incluses par l’URLconf du projet sous `/api/v1/livreur/`. Les tests n’ont pas été exécutés dans le cadre de la rédaction de ce rapport.
