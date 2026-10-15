# MODULE accounts — Document de conception technique

Objectif du document : décrire de manière exhaustive le module accounts avant toute implémentation. Ce document sert de référence contractuelle pour l'équipe : tout développeur qui touche à accounts doit d'abord lire ce fichier.

# 📑 Plan du document
## Partie 1 — Compréhension du module
### 1.1. Vue d'ensemble — à quoi sert accounts en une page
Le module accounts est la fondation de toute la plateforme Mashop Livraison. Il a une seule mission : gérer l'identité de chaque personne qui interagit avec le système, et contrôler ce que cette personne a le droit de faire.

Concrètement, accounts répond à trois questions essentielles pour le reste de la plateforme :

Qui es-tu ? → c'est l'authentification (vérifier ton identité via email/mot de passe ou via une clé API)

Quel est ton rôle ? → c'est la gestion des rôles (Administrateur, Partenaire, Livreur)

Qu'as-tu le droit de faire ? → c'est l'autorisation (permissions attachées à chaque rôle)

Sans ce module, aucune autre partie du système ne peut fonctionner : la création d'une course, l'acceptation d'une livraison, la consultation d'un tableau de bord — tout dépend du fait que l'utilisateur soit d'abord identifié et reconnu.

En une phrase : accounts est le portier de la plateforme. Il vérifie l'identité, attribue un rôle, et laisse passer (ou refuse) chaque requête vers les autres modules.
### 1.2. Position dans l'architecture — schéma des dépendances avec les autres apps
accounts occupe une position centrale dans l'architecture, mais avec une particularité importante : il ne dépend d'aucun autre module. C'est une dépendance unidirectionnelle.

Autrement dit :
accounts ne connaît pas courses, logistics, partners ni drivers

En revanche, tous les autres modules dépendent de accounts

Cette asymétrie est volontaire. Elle garantit que la fondation reste stable : on peut modifier courses sans jamais risquer de casser accounts. L'inverse n'est pas vrai, et c'est normal.


Schéma conceptuel des dépendances
                    ┌─────────────────────┐
                    │      accounts       │  ← Aucune dépendance interne
                    │   (la fondation)    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │ courses  │     │ partners │     │ drivers  │
        └────┬─────┘     └────┬─────┘     └────┬─────┘
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                        ┌──────────┐
                        │logistics │
                        └──────────┘
### 1.3. Vocabulaire métier — définitions précises des termes (User, Partenaire, Livreur, CléAPI, Rôle…)
Pour éviter toute ambiguïté dans l'équipe, voici les termes officiels du module. Ces mots doivent être utilisés exactement dans ce sens, dans le code comme dans les discussions.
#### User (Utilisateur)
Compte d'identification de base. Représente une personne qui peut se connecter à la plateforme. Contient les informations d'authentification (email, mot de passe haché, statut actif/inactif) et un rôle qui détermine son type d'accès.

⚠️ Ne pas confondre User (l'identité) avec Partenaire ou Livreur (les profils métier attachés à cette identité).

##### Rôle
Étiquette attachée à un User qui détermine ce qu'il peut faire dans le système. Trois rôles existent :

* ADMIN — l'administrateur de la plateforme (créé manuellement par le superuser Django)

* PARTENAIRE — une boutique ou entreprise qui crée des demandes de livraison

* LIVREUR — une personne qui prend en charge et effectue les livraisons

Un User a un seul et unique rôle, défini à sa création, non modifiable sans action d'un ADMIN.

#### Partenaire
Profil métier attaché à un User de rôle PARTENAIRE. Contient les informations commerciales : nom de la boutique, URL de webhook (pour recevoir les notifications), statut actif/inactif.

Un User de rôle PARTENAIRE a exactement un profil Partenaire. La relation est 1-à-1.

#### Livreur
Profil métier attaché à un User de rôle LIVREUR. Contient les informations opérationnelles : disponibilité actuelle, statut actif/inactif.

Un User de rôle LIVREUR a exactement un profil Livreur. La relation est 1-à-1.

#### Clé API
Moyen d'authentification alternatif au JWT, réservé aux partenaires. Permet à un système externe (le backend du partenaire) d'appeler notre API sans passer par un écran de connexion. C'est un secret long (type pk_live_xxxxxxxx), généré par l'ADMIN, stocké haché côté serveur, et transmis au partenaire une seule fois au moment de sa création.

La clé API n'est pas un mot de passe. Elle ne permet pas de se connecter à l'interface web. Elle sert uniquement aux appels API serveur-à-serveur.

##### Authentification
Processus qui consiste à vérifier l'identité d'un utilisateur. Dans notre système, deux mécanismes coexistent :

    JWT (JSON Web Token) → pour l'ADMIN ,PARTENAIRE et le LIVREUR

    Clé API → autre alternative pour le PARTENAIRE

##### Autorisation
Processus qui consiste à vérifier qu'un utilisateur authentifié a le droit d'accéder à une ressource ou d'effectuer une action. Exemple : un LIVREUR authentifié n'a pas le droit de créer un partenaire, même s'il est bien identifié.

##### Restriction (d'accès aux données)
Processus qui consiste à limiter la visibilité d'un utilisateur à ses propres données. Exemple : un PARTENAIRE authentifié a le droit de consulter ses courses, mais pas celles d'un autre partenaire.

Distinction cruciale : l'autorisation parle de « type d'action », la restriction parle de « à qui appartient la donnée ». Les deux sont obligatoires.

##### Superuser (Django)
Compte administrateur technique créé en ligne de commande lors du déploiement. Il n'est pas géré par le module accounts au sens métier : il sert à créer les premiers ADMIN, à accéder à l'interface d'administration Django, et à effectuer des opérations de maintenance. Le superuser n'apparaît pas dans les endpoints publics de notre API.

### 1.4. Périmètre — ce que le module fait ET ce qu'il ne fait pas
Cette section est essentielle pour éviter les dérives. Chaque fois qu'un développeur se demande « est-ce que ça appartient à accounts ? », il doit consulter cette liste.

✅ Ce que accounts fait

* Créer un compte ADMIN (via superuser), un compte PARTENAIRE ou un compte LIVREUR (via ADMIN)

* Authentifier un utilisateur (login avec email + mot de passe, ou clé API)

* Émettre les JWT (access + refresh) après un login réussi

* Valider un JWT à chaque requête

* Valider une clé API à chaque requête partenaire

* Générer, révoquer et stocker les clés API des partenaires

* Gérer les rôles et exposer les permissions (IsAdmin, IsPartenaire, IsLivreur)

* Activer / désactiver un compte utilisateur

* Consulter son propre profil (/me/)

* Lister, créer, modifier, désactiver les partenaires et les livreurs (réservé à l'ADMIN)

❌❌❌ Ce que accounts ne fait PAS❌❌❌
❌ Gérer les courses → appartient à courses
❌ Gérer les zones et tarifs → appartient à logistics
❌ Envoyer des webhooks → appartient à partners
❌ Gérer les disponibilités des livreurs en temps réel → appartient à drivers
❌ Calculer un prix de livraison → appartient à logistics
❌ Stocker des informations métier (nom de destinataire, description de colis, etc.) → appartient à courses
❌ Exposer des endpoints publics (voir 1.5)
❌ Créer des comptes sans validation de l'ADMIN (sauf le superuser, hors API)

### 1.5. Principe fondateur : aucun endpoint public
C'est la règle la plus importante du module. Elle doit être comprise et respectée par toute l'équipe.

Énoncé de la règle
Dans le module accounts, aucun endpoint n'est public au sens strict.

Cela signifie qu'aucune donnée n'est accessible sans preuve d'identité. Toute requête qui n'est pas accompagnée d'un JWT valide ou d'une clé API valide est immédiatement rejetée.

Énoncé de la règle
Dans le module accounts, aucun endpoint n'est public au sens strict.

Cela signifie qu'aucune donnée n'est accessible sans preuve d'identité. Toute requête qui n'est pas accompagnée d'un JWT valide ou d'une clé API valide est immédiatement rejetée.

* Pourquoi cette règle ?
Historiquement, beaucoup d'applications exposent des endpoints de consultation « libre » (lister des utilisateurs, voir des profils, etc.). Cela a causé de nombreuses fuites de données dans des projets réels : noms, emails, numéros de téléphone, adresses, parfois même mots de passe hachés.

Pour Mashop Livraison, nous appliquons le principe inverse : rien n'est visible par défaut. Pour voir quoi que ce soit, il faut :
- Prouver son identité (authentification)
- Avoir le bon rôle (autorisation)
- Être propriétaire de la donnée ou avoir un rôle qui autorise la vue globale (restriction)

* Conséquences concrètes pour l'équipe
Pour le backend :

La configuration globale du framework devra refuser toute requête non authentifiée par défaut

Chaque vue devra explicitement déclarer son mécanisme d'authentification (JWT, API Key, ou exception login/refresh)

Un endpoint non déclaré → refus automatique (401)

- Pour le frontend React :

Aucune page ne peut afficher de données sans avoir d'abord obtenu un token ou une clé

Le premier écran affiché à un visiteur est nécessairement l'écran de connexion

Après login, le token doit être stocké de façon sécurisée et envoyé à chaque requête

Toute réponse 401 doit déclencher une redirection vers l'écran de connexion

Aucun composant ne doit contenir de données « en dur » qui ne proviendraient pas de l'API

- Pour les tests :

Chaque test d'endpoint doit commencer par vérifier que sans token, la réponse est 401

Ensuite seulement, on teste le comportement avec un token valide

Les tests de permissions vérifient qu'un rôle insuffisant → 403

Les tests de restriction vérifient qu'un utilisateur non propriétaire → 404

* Récapitulatif visuel

Requête entrante
      │
      ▼
┌──────────────────┐
│ Token fourni ?   │── NON ──▶ 401 Unauthorized
└────────┬─────────┘
         │ OUI
         ▼
┌──────────────────┐
│ Token valide ?   │── NON ──▶ 401 Unauthorized
└────────┬─────────┘
         │ OUI
         ▼
┌──────────────────┐
│ Rôle autorisé ?  │── NON ──▶ 403 Forbidden
└────────┬─────────┘
         │ OUI
         ▼
┌──────────────────┐
│ Propriétaire ?   │── NON ──▶ 404 Not Found
└────────┬─────────┘
         │ OUI
         ▼
    ✅ Accès autorisé

Cette règle est non négociable et sera reprise en détail dans la Partie 5 (Restriction d'accès aux données).

## Partie 2 — Fonctionnement interne
### 2.1. Modèle conceptuel de données — les 4 entités et leurs relations (sans SQL)
Le module accounts s'appuie sur quatre entités conceptuelles qui couvrent l'ensemble de ses responsabilités. Avant de décrire leurs relations, rappelons ce que le rapport de conception du groupe impose : le modèle Utilisateur (tel que décrit dans le diagramme de classes, figure 2) contient les attributs idUtilisateur, nom, prenom, email, telephone, motDePasse, role, ainsi que deux opérations : sAuthentifier() et seDeconnecter(). Les trois acteurs métier (Administrateur, Partenaire, Livreur) héritent tous de cette classe Utilisateur.

Notre conception backend traduit ce modèle en quatre entités persistantes :

#### Entité 1 — Utilisateur (User)
Représente l'identité de connexion. C'est l'entité centrale dont dérivent toutes les autres. Elle contient :

- Un identifiant unique (généré par le système)

- Les informations nominatives : nom, prénom

- Les coordonnées : email (unique, sert d'identifiant de connexion), téléphone

- Le secret d'authentification : mot de passe, stocké sous forme hachée

- Le rôle : ADMIN, PARTENAIRE ou LIVREUR (un seul rôle par utilisateur)

- Le statut : actif ou inactif (booléen qui conditionne l'accès)

Conformément au rapport de conception, Utilisateur porte l'opération sAuthentifier(). En backend, cette opération ne sera pas une méthode sur le modèle mais un service d'authentification (voir 2.3). Elle porte également seDeconnecter(), qui sera traduit par l'invalidation du token côté serveur.

#### Entité 2 — Administrateur
L'administrateur n'a pas d'entité dédiée. C'est un Utilisateur dont le rôle vaut ADMIN. Il est créé en dehors de l'API (via la commande de création de superutilisateur de Django), puis peut ensuite créer d'autres utilisateurs.

Le rapport de conception distingue conceptuellement Administrateur comme une classe à part entière (avec des opérations comme genereUtilisateur, gereTarifs, assignerCourse, etc.). En backend, nous choisissons de ne pas créer de table Administrateur : ses opérations sont réparties dans les modules accounts (pour genereUtilisateur, gererPartenaires, gererLivreurs, genererCleAPI) et dans les autres modules (courses pour assignerCourse, logistics pour gereTarifs). Cette décision évite une table vide qui ne porterait aucun attribut propre. Elle sera documentée dans les décisions de conception 

#### Entité 3 — Partenaire
Profil métier attaché à un Utilisateur de rôle PARTENAIRE. Contient les informations commerciales nécessaires à son activité de livraison :

- Un lien vers l'Utilisateur (relation 1-à-1)
- Le nom de la boutique (raison sociale)
- L'URL de webhook (adresse à laquelle notre système notifiera les changements de statut des courses)
- Le statut actif/inactif (permet de désactiver un partenaire sans le supprimer)

Le rapport mentionne l'opération genererCleAPI() côté Administrateur. Cette opération produit une Clé API rattachée au Partenaire 

#### Entité 4 — Clé API (CleAPI)
Secret d'authentification alternatif au JWT, réservé aux partenaires. Permet à un système externe (le backend du partenaire) d'appeler notre API sans passer par un écran de connexion. 

Contient :
- Un lien vers le Partenaire (relation plusieurs-à-1 : un partenaire peut avoir plusieurs clés au fil du temps, mais une seule active)
- Le préfixe de la clé (portion visible, utilisée pour identifier la clé sans révéler le secret)
- Le hash de la clé (seul le hash est stocké — jamais la clé en clair)
- Le statut : active ou révoquée
- Les dates : date de création, date de révocation

Le rapport de conception insiste sur la sécurité : « stocker les clés API sous forme hachée ». Cette exigence est traduite directement par le champ hash de cette entité.

#### Entité 5 — Livreur (persistée)
Profil métier attaché à un Utilisateur de rôle LIVREUR. Contient les informations opérationnelles nécessaires à son activité :

Un lien vers l'Utilisateur (relation 1-à-1)

La disponibilité : booléen indiquant si le livreur est prêt à accepter une course

Le statut actif/inactif (permet de désactiver un livreur sans le supprimer)

Le rapport de conception décrit le Livreur avec ses opérations propres (accepterAffectation(), refuserAffectation(), marquerRécupéré(), validerLivraison(), consulterHistorique()). En backend, ces opérations sont réparties dans le module drivers, tandis que les attributs (disponible, actif) restent dans la table Livreur du module accounts.


┌─────────────────────────────┐
│       UTILISATEUR           │
│  (persisté)                 │
│  - id                       │
│  - nom, prénom              │
│  - email (unique)           │
│  - téléphone                │
│  - mot de passe (haché)     │
│  - rôle (ADMIN/PART./LIV.)  │
│  - actif (bool)             │
└──────────────┬──────────────┘
               │
  ┌────────────┼────────────────────┐
  │            │                    │
  │ rôle=ADMIN │ rôle=PARTENAIRE    │ rôle=LIVREUR
  │            │                    │
  ▼            ▼                    ▼
┌─────────────────────┐  ┌──────────────┐   ┌──────────────┐
│   ADMINISTRATEUR    │  │  PARTENAIRE  │   │   LIVREUR    │
│  (non persisté —    │  │  (persisté)  │   │  (persisté)  │
│   simple rôle)      │  │              │   │              │
│                     │  │ - nom_boutiq.│   │ - disponible │
│  Aucune table       │  │ - url_webhook│   │ - actif      │
│  dédiée : ses       │  │ - actif      │   │              │
│  opérations sont    │  │              │   │              │
│  réparties dans     │  └──────┬───────┘   └──────────────┘
│  accounts et les    │         │
│  autres modules     │         │  1-à-plusieurs
└─────────────────────┘         │  (une seule active
                                │   à la fois)
                                ▼
                        ┌──────────────┐
                        │   CLÉ API    │
                        │  (persisté)  │
                        │              │
                        │ - préfixe    │
                        │ - hash       │
                        │ - statut     │
                        │ - dates      │
                        └──────────────┘
Description détaillée des relations
Relation 1 — Utilisateur → Administrateur
Aspect	Détail
Type	Spécialisation par rôle (non persistée)
Cardinalité	Un Utilisateur de rôle ADMIN est un Administrateur
Persistance	Aucune table dédiée — le rôle suffit à identifier l'Administrateur
Justification	L'Administrateur n'a pas d'attributs propres en dehors de ceux de l'Utilisateur
Relation 2 — Utilisateur → Partenaire
Aspect	Détail
Type	Association 1-à-1
Cardinalité	Un Utilisateur de rôle PARTENAIRE a exactement un Partenaire
Obligatoire	Oui — un Partenaire ne peut exister sans Utilisateur
Persistance	Table Partenaire avec clé étrangère unique vers Utilisateur
Relation 3 — Utilisateur → Livreur
Aspect	Détail
Type	Association 1-à-1
Cardinalité	Un Utilisateur de rôle LIVREUR a exactement un Livreur
Obligatoire	Oui — un Livreur ne peut exister sans Utilisateur
Persistance	Table Livreur avec clé étrangère unique vers Utilisateur
Relation 4 — Partenaire → Clé API
Aspect	Détail
Type	Association 1-à-plusieurs
Cardinalité	Un Partenaire peut avoir plusieurs clés au fil du temps
Contrainte	Une seule clé active à un instant donné
Obligatoire	Non — un partenaire peut exister sans clé (mais ne peut pas appeler l'API)
Persistance	Table Clé API avec clé étrangère vers Partenaire
Règles structurelles à retenir
Un Utilisateur a un seul rôle — jamais deux. Le rôle est fixé à la création.

Un Utilisateur de rôle PARTENAIRE a un et un seul Partenaire — relation 1-à-1 stricte.

Un Utilisateur de rôle LIVREUR a un et un seul Livreur — relation 1-à-1 stricte.

Un Partenaire peut avoir plusieurs clés API dans le temps, mais une seule active à un instant donné. Générer une nouvelle clé révoque automatiquement l'ancienne.

L'Administrateur n'est pas une table — c'est un Utilisateur dont le rôle vaut ADMIN.

L'email est unique dans toute la table Utilisateur.

### 2.2. Cycle de vie d'un compte — de la création à la désactivation
Le cycle de vie décrit les états par lesquels passe un compte depuis sa création jusqu'à sa fin de vie. Cette section est cruciale car elle conditionne toutes les règles de sécurité (voir Partie 5) et les règles métier (voir Partie 6). Elle s'applique aux trois types de comptes : ADMIN, PARTENAIRE et LIVREUR.

Vue d'ensemble des états possibles
Tout compte du système passe par un ou plusieurs de ces cinq états :

État	Description	Accès possible
Créé	Le compte existe en base mais n'a pas encore été utilisé	Aucun
Actif	Le compte est utilisable normalement	Selon le rôle
Désactivé	Le compte est temporairement bloqué par un ADMIN	Aucun
Réactivé	Le compte désactivé a été remis en service	Selon le rôle
Supprimé	État théorique — jamais atteint si le compte a des données liées	—

Diagramme des transitions d'état
text
                    ┌─────────────────────────────┐
                    │                             │
                    ▼                             │
              [ CRÉÉ ] ──▶ [ ACTIF ] ──▶ [ DÉSACTIVÉ ] ──▶ [ SUPPRIMÉ ]
                              ▲                │             (interdit
                              │                │              si données
                              │                │              liées)
                              └────────────────┘
                              (réactivation
                               par l'ADMIN)

Lecture du diagramme :

Un compte créé devient actif immédiatement (pas d'étape de validation par email dans cette version).

Un compte actif peut être désactivé par un ADMIN.

Un compte désactivé peut être réactivé par un ADMIN.

Un compte avec des données métier liées (courses pour un partenaire ou un livreur) ne peut jamais être supprimé — seulement désactivé.

##### Cycle de vie d'un compte ADMIN
1. Création (hors API)
L'administrateur initial est créé en dehors de l'API, via une commande en ligne de commande réservée au superutilisateur Django. Cette création se fait avant le démarrage de la plateforme ou lors d'une opération de maintenance.

Caractéristiques :

Aucun endpoint API ne permet de créer un ADMIN.

L'ADMIN n'est donc pas un compte que l'on crée « depuis l'interface ».

Le superutilisateur qui crée l'ADMIN est un compte technique distinct, non exposé par l'API.

2. Activation immédiate
Dès sa création, le compte ADMIN est actif. Il n'y a pas d'étape de validation intermédiaire.

3. Utilisation courante
L'ADMIN se connecte via /auth/login/ (mécanisme JWT) et peut alors :

Créer des comptes PARTENAIRE

Créer des comptes LIVREUR

Générer ou révoquer des clés API

Consulter les données globales de la plateforme (via les autres modules)

4. Désactivation
Un ADMIN ne peut pas être désactivé par un autre ADMIN via l'API. Cette restriction est volontaire :

Elle protège contre les abus internes (un ADMIN ne peut pas bloquer un autre ADMIN).

La désactivation d'un ADMIN est une opération technique, réalisée par le superutilisateur en ligne de commande.

5. Suppression
Un ADMIN ne peut pas être supprimé via l'API. Sa suppression relève également d'une opération technique hors API.

##### Cycle de vie d'un compte PARTENAIRE
1. Création par l'ADMIN
L'ADMIN appelle l'endpoint de création de partenaire en fournissant :

Nom et prénom du responsable

Email (unique dans tout le système)

Téléphone

Mot de passe temporaire

Nom de la boutique

URL de webhook (optionnelle)

Règles à la création :

L'email doit être unique.

Le nom de boutique doit être unique parmi les partenaires actifs.

Le mot de passe temporaire est communiqué au partenaire par un canal sécurisé (jamais par email non chiffré).

2. Génération automatique de la clé API
À la création du partenaire, une première clé API est générée automatiquement. Cette clé :

Est affichée une seule fois à l'ADMIN au moment de la réponse à la création.

N'est jamais récupérable ensuite (seul son hash est stocké).

Doit être transmise au partenaire par un canal sécurisé.

Permet au partenaire de commencer immédiatement à appeler l'API sans attendre sa première connexion.

3. Activation
Le compte est immédiatement actif. Le partenaire peut commencer à utiliser sa clé API dès sa réception.

4. Première connexion
Le partenaire utilise soit :

Sa clé API (depuis son propre backend) — cas le plus courant

Son email + mot de passe temporaire (via le frontend React) — cas exceptionnel

Dans le second cas, il est invité à changer son mot de passe temporaire lors de sa première connexion.

5. Utilisation courante
Le partenaire utilise la plateforme pour :

Créer des demandes de livraison (courses)

Consulter le statut de ses courses

Annuler des courses (selon les statuts autorisés)

Recevoir des webhooks sur les changements de statut

6. Désactivation
L'ADMIN peut désactiver un partenaire à tout moment.

Règles de désactivation :

Si le partenaire a des courses en cours (non terminées : créée, acceptée, récupérée), un avertissement est requis avant la désactivation.

Si le partenaire a des courses existantes (même terminées), la suppression est impossible — seule la désactivation est autorisée.

La désactivation d'un partenaire révoque automatiquement toutes ses clés API actives.

Effet de la désactivation :

Le partenaire ne peut plus s'authentifier (ni par clé API, ni par email/mot de passe).

Les endpoints /partenaire/* retournent 403 Forbidden.

7. Réactivation
Un partenaire désactivé peut être réactivé par l'ADMIN. La réactivation :

Rétablit l'accès du partenaire.

Ne réactive pas les clés API révoquées — il faut en générer une nouvelle.

Conserve l'historique des courses du partenaire.

8. Suppression
Impossible si le partenaire a des courses existantes. La suppression est remplacée par une désactivation (conformément à la spécification non fonctionnelle « Intégrité des données » du rapport de conception).

##### Cycle de vie d'un compte LIVREUR
1. Création par l'ADMIN
L'ADMIN appelle l'endpoint de création de livreur en fournissant :

Nom et prénom

Email (unique dans tout le système)

Téléphone

Mot de passe temporaire

Règles à la création :

L'email doit être unique.

Le mot de passe temporaire est communiqué au livreur par un canal sécurisé.

2. Activation
Le compte est immédiatement actif. Le livreur peut se connecter dès réception de ses identifiants.

3. Première connexion
Le livreur se connecte via /auth/login/ (mécanisme JWT) avec son email et son mot de passe temporaire. Il est invité à changer son mot de passe lors de sa première connexion.

4. Gestion de la disponibilité
Le livreur peut se déclarer disponible ou indisponible :

Disponible → il voit les courses disponibles à accepter.

Indisponible → il ne reçoit pas de nouvelles propositions de courses.

Cette disponibilité est un attribut propre au livreur, utilisé par le module drivers pour filtrer les courses proposées.

5. Utilisation courante
Le livreur utilise la plateforme pour :

Voir les courses disponibles

Accepter une course

Marquer un colis comme récupéré

Livrer avec code de confirmation

Cocher le paiement

Consulter son historique du jour

6. Désactivation
L'ADMIN peut désactiver un livreur à tout moment.

Règles de désactivation :

Si le livreur a des courses en cours (acceptée ou récupérée), un avertissement est requis (conformément au rapport de conception : « Désactivation d'un livreur avec courses en cours : avertissement »).

Si le livreur a des courses existantes (même terminées), la suppression est impossible — seule la désactivation est autorisée.

Effet de la désactivation :

Le livreur ne peut plus s'authentifier.

Les endpoints /livreur/* retournent 403 Forbidden.

Ses courses en cours doivent être réassignées par l'ADMIN (via le module courses).

7. Réactivation
Un livreur désactivé peut être réactivé par l'ADMIN. La réactivation :

Rétablit l'accès du livreur.

Conserve l'historique de ses courses.

Le livreur redevient indisponible par défaut — il doit se redéclarer disponible.

8. Suppression
Impossible si le livreur a des courses existantes. La suppression est remplacée par une désactivation.

##### Cycle de vie d'une Clé API
1. Génération
La clé API est générée automatiquement à la création du partenaire, ou manuellement par l'ADMIN via un endpoint dédié.

Caractéristiques :

Le système produit un secret aléatoire de longueur suffisante.

Un préfixe (court et lisible) est ajouté pour identification visuelle.

Le hash du secret est stocké ; le secret en clair n'est jamais persisté.

2. Affichage unique
La clé en clair est affichée une seule fois à l'ADMIN au moment de la génération. Elle n'est jamais récupérable ensuite.

3. Utilisation
Le partenaire envoie sa clé dans chaque requête API (via un en-tête HTTP dédié). Le système hache la clé reçue et la compare aux hashes stockés.

4. Révocation
La révocation peut être explicite (par l'ADMIN) ou automatique dans deux cas :

Le partenaire est désactivé → toutes ses clés sont révoquées.

Une nouvelle clé est générée pour le même partenaire → l'ancienne est automatiquement révoquée.

Caractéristiques de la révocation :

Immédiate : la clé est inutilisable dès la révocation.

Irréversible : une clé révoquée ne peut pas être réactivée.

Traçable : la date de révocation est enregistrée.

5. Régénération
L'ADMIN peut générer une nouvelle clé pour un partenaire à tout moment. La régénération :

Crée une nouvelle clé active.

Révoque automatiquement l'ancienne clé active (s'il y en avait une).

Affiche la nouvelle clé en clair une seule fois.

Tableau récapitulatif des actions par acteur
Action	                    ADMIN	                        PARTENAIRE	LIVREUR
Créer un ADMIN	            ❌ (hors API)	                ❌	        ❌
Créer un PARTENAIRE	        ✅	                            ❌	        ❌
Créer un LIVREUR	        ✅	                            ❌	        ❌
Activer son propre compte	 —                                —	            —
Se désactiver soi-même	    ❌	                            ❌	        ❌
Désactiver un PARTENAIRE    ✅	                            ❌	        ❌
Désactiver un LIVREUR	    ✅	                            ❌	        ❌
Réactiver un PARTENAIRE	    ✅	                            ❌	        ❌
Réactiver un LIVREUR	    ✅	                            ❌	        ❌
Supprimer un PARTENAIRE	    ❌ (désactivation uniquement)	❌	        ❌
Supprimer un LIVREUR	    ❌ (désactivation uniquement)	❌	        ❌
Générer une clé API	        ✅	                            ❌	        ❌
Révoquer une clé API	    ✅	                            ❌	        ❌

#### Règles de cycle de vie à retenir
Aucun compte ne peut être supprimé s'il a des données métier liées (courses). La désactivation remplace la suppression.

Un ADMIN ne peut pas désactiver un autre ADMIN via l'API — protection contre les abus internes.

La désactivation d'un partenaire révoque automatiquement ses clés API — pas de clé active sur un compte inactif.

La réactivation d'un partenaire ne réactive pas ses anciennes clés — il faut en générer une nouvelle.

La désactivation d'un livreur avec courses en cours nécessite un avertissement explicite.

Un livreur réactivé repasse en « indisponible » — il doit se redéclarer disponible.

La suppression d'un ADMIN est une opération technique hors API.


### 2.3. Mécanismes d'authentification — JWT vs API Key, quand utiliser lequel
Le module accounts propose deux mécanismes d'authentification, mais leur rôle est asymétrique : le JWT est le mécanisme principal et universel, la clé API est une alternative optionnelle réservée au partenaire.

* Principe fondateur
Tout le monde utilise le JWT en premier.
La clé API est une alternative que le partenaire peut utiliser en plus du JWT, pour des usages spécifiques.

Cela signifie concrètement :
- L'ADMIN utilise uniquement le JWT.
- Le LIVREUR utilise uniquement le JWT.
- Le PARTENAIRE utilise le JWT (via le frontend React) et peut aussi utiliser la clé API (depuis son propre backend), selon le contexte.

Autrement dit : la clé API n'est jamais obligatoire. Un partenaire qui n'utilise que le frontend React peut parfaitement fonctionner sans jamais générer de clé API.

#### Mécanisme 1 — JWT (mécanisme principal, universel)
Public visé
Tous les acteurs : ADMIN, PARTENAIRE, LIVREUR.

* Principe général
L'utilisateur se connecte avec son email et son mot de passe. Si les identifiants sont valides, le serveur retourne deux tokens :

Un access token — de courte durée (par exemple 30 minutes). Envoyé à chaque requête API dans un en-tête HTTP.

Un refresh token — de plus longue durée (par exemple 7 jours). Sert uniquement à obtenir un nouvel access token quand celui-ci a expiré.

* Pourquoi deux tokens ?
Pour limiter les dégâts en cas de vol :

Si un access token est volé, il expire rapidement (30 min).
Le refresh token, plus sensible, n'est utilisé que sur un endpoint dédié (/auth/refresh/).

* Flux d'authentification JWT
L'utilisateur envoie email + mot de passe à /auth/login/.

- Le serveur vérifie les identifiants et vérifie que le compte est actif.

- Le serveur retourne les deux tokens + les informations de profil (dont le rôle).

- Le frontend React stocke les tokens de façon sécurisée (idéalement : refresh token en cookie httpOnly, access token en mémoire).

- À chaque requête API, l'access token est envoyé dans l'en-tête Authorization: Bearer <token>.

- Si l'access token est expiré (réponse 401), le frontend appelle /auth/refresh/ avec le refresh token pour en obtenir un nouveau.

- Si le refresh token est expiré ou révoqué, l'utilisateur doit se reconnecter.

- Cas d'usage typiques
ADMIN se connectant au tableau de bord depuis son navigateur

- LIVREUR consultant ses courses disponibles sur son téléphone

- PARTENAIRE se connectant au frontend React pour créer une course manuellement

- Tout utilisateur naviguant sur l'interface React

* Caractéristiques
Aspect	Valeur
Public	ADMIN, PARTENAIRE, LIVREUR
Type d'utilisateur	Humain, via interface web ou mobile
Origine	Email + mot de passe
En-tête HTTP	Authorization: Bearer <token>
Durée de vie	Courte (access) + longue (refresh)
Révocable	Oui (logout, blacklist du refresh)
Rotation	Automatique (via refresh)

Public visé
Uniquement le PARTENAIRE, et uniquement en complément du JWT.

Principe général
Le partenaire dispose d'un secret long (type pk_live_xxxxxxxx), généré par l'ADMIN, qu'il envoie dans un en-tête HTTP dédié (X-API-Key: <clé>) à chaque requête. Le serveur hache la clé reçue et compare au hash stocké.

Pourquoi une clé API en plus du JWT ?
Parce qu'un partenaire est aussi un système informatique, pas seulement un humain devant un écran. Il a deux contextes d'utilisation :

Contexte	Mécanisme adapté
Un humain du partenaire se connecte au frontend React	JWT (email + mot de passe)
Le backend du partenaire appelle notre API automatiquement	Clé API (pas d'écran, pas de session)
La clé API permet au partenaire d'intégrer notre plateforme dans son propre système sans avoir à gérer un login interactif.

* Flux d'authentification par clé API
Le partenaire envoie une requête à un endpoint /api/v1/partenaire/* avec l'en-tête X-API-Key: pk_live_xxxxxxxx.

Le serveur hache la clé reçue et la compare aux hashes stockés.

Si une clé correspond et est active, le serveur identifie le partenaire associé.

Le serveur traite la requête au nom de ce partenaire.

Si la clé est invalide ou révoquée, le serveur retourne 401.

Cas d'usage typiques
Le backend du partenaire (Kivu Shop, Mama Mode, Goma Tech, etc.) appelle notre API pour créer une course automatiquement.

Le backend du partenaire interroge le statut d'une course à intervalles réguliers.

Le backend du partenaire annule une course suite à une action de son propre utilisateur.

Comparaison des deux mécanismes
Critère	JWT	Clé API
Public	ADMIN, PARTENAIRE, LIVREUR	PARTENAIRE uniquement
Type d'utilisateur	Humain (interface web/mobile)	Système (serveur-à-serveur)
Origine	Email + mot de passe	Généré par l'ADMIN
En-tête HTTP	Authorization: Bearer <token>	X-API-Key: <clé>
Durée de vie	Courte (access) + longue (refresh)	Longue (jusqu'à révocation)
Révocable	Oui (logout)	Oui (par l'ADMIN)
Rotation	Automatique (refresh)	Manuelle (régénération)
Stockage serveur	Aucun (le JWT est auto-porteur)	Hash en base
Stockage client	Mémoire + cookie httpOnly	Variable d'environnement du partenaire
Obligatoire ?	Oui, pour tout le monde	Non, optionnelle pour le partenaire

#### Règles d'utilisation
Règle 1 — Le JWT est toujours disponible pour tout le monde
Tous les acteurs peuvent se connecter via /auth/login/ et obtenir un JWT. Aucun acteur n'est exclu du JWT.

Règle 2 — La clé API est un mécanisme supplémentaire, pas un remplacement
Un partenaire peut utiliser le JWT seul, la clé API seule, ou les deux selon le contexte. Les deux mécanismes peuvent coexister pour le même partenaire.

Règle 3 — L'ADMIN et le LIVREUR n'ont pas accès à la clé API
Seul le PARTENAIRE peut obtenir et utiliser une clé API. Cette restriction est une décision de sécurité : elle limite la surface d'attaque et évite qu'une clé compromise ne donne accès à l'interface d'administration ou aux endpoints livreur.

Règle 4 — Chaque endpoint déclare explicitement le(s) mécanisme(s) accepté(s)
Un endpoint peut accepter :

JWT uniquement → cas standard (admin, livreur)

JWT ou clé API → cas du partenaire (il choisit selon son contexte)

Aucun (login, refresh) → portes d'entrée d'authentification

Chaque endpoint documente clairement son ou ses mécanismes acceptés.

Règle 5 — Un partenaire peut passer de l'un à l'autre sans friction
Le même partenaire peut :

Se connecter au frontend React avec son email/mot de passe → reçoit un JWT

Appeler l'API depuis son backend avec sa clé API → utilise l'en-tête X-API-Key

Les deux modes d'accès sont indépendants mais mènent au même partenaire.

Impact sur les endpoints du module accounts
Endpoint	Mécanisme accepté	Public
/auth/login/	Aucun (porte d'entrée)	Tous
/auth/refresh/	Refresh token (porte d'entrée)	Tous
/auth/me/	JWT	ADMIN, PARTENAIRE, LIVREUR
/admin/*	JWT	ADMIN uniquement
/partenaire/*	JWT ou clé API	PARTENAIRE uniquement
/livreur/*	JWT	LIVREUR uniquement
Note importante : les endpoints /partenaire/* acceptent les deux mécanismes. C'est le seul espace où la clé API est autorisée. Ailleurs, seul le JWT fonctionne.




### 2.4. Gestion des rôles et permissions — qui peut faire quoi
Le module accounts définit trois rôles et quatre permissions de base qui sont utilisées dans toute la plateforme. Cette section précise qui peut faire quoi, à la fois dans accounts et dans les autres modules.

Les trois rôles
Un rôle est une étiquette unique attachée à un Utilisateur. Il détermine son type d'accès et les opérations qu'il peut effectuer.

Rôle	Description	Créé par
ADMIN	Administrateur de la plateforme. Accès global à toutes les données et à toutes les opérations d'administration.	Superutilisateur (hors API)
PARTENAIRE	Boutique ou entreprise qui crée des demandes de livraison. Accès restreint à ses propres données.	ADMIN
LIVREUR	Personne qui prend en charge et effectue les livraisons. Accès restreint à ses propres courses.	ADMIN

Règles sur les rôles
Un Utilisateur a un seul et unique rôle. Jamais deux, jamais zéro.

Le rôle est fixé à la création du compte. Il ne peut pas être modifié via l'API.

Un Utilisateur ne peut pas changer son propre rôle.

Un ADMIN ne peut pas changer le rôle d'un autre utilisateur (créer un nouveau compte est la seule façon de changer de rôle).

Cette rigidité est volontaire : elle évite les élévations de privilèges accidentelles ou malveillantes.

Les quatre permissions de base
Le module accounts expose quatre permissions qui sont utilisées par tous les endpoints de la plateforme.

Permission	Signification	Contexte d'utilisation
EstAuthentifié	L'utilisateur a fourni un JWT valide ou une clé API valide.	Tous les endpoints protégés
EstAdmin	L'utilisateur a le rôle ADMIN et s'est authentifié par JWT.	Endpoints /admin/*
EstPartenaire	L'utilisateur a le rôle PARTENAIRE et s'est authentifié (JWT ou clé API).	Endpoints /partenaire/*
EstLivreur	L'utilisateur a le rôle LIVREUR et s'est authentifié par JWT.	Endpoints /livreur/*


Hiérarchie des permissions
Les permissions ne sont pas hiérarchiques entre elles. Un ADMIN n'a pas automatiquement la permission EstPartenaire — il a EstAdmin, ce qui lui donne accès aux endpoints admin.

text
EstAuthentifié  ←  condition minimale pour tout endpoint protégé
     │
     ├── EstAdmin      →  endpoints /admin/*
     ├── EstPartenaire →  endpoints /partenaire/*
     └── EstLivreur    →  endpoints /livreur/*
Conséquence pratique : un endpoint /admin/* n'accepte que les utilisateurs ayant la permission EstAdmin. Un PARTENAIRE authentifié qui tente d'accéder à /admin/* reçoit 403 Forbidden (il est authentifié mais n'a pas le bon rôle).

Qui peut faire quoi — dans le module accounts
Action	ADMIN	PARTENAIRE	LIVREUR
Se connecter via /auth/login/	✅	✅	✅
Rafraîchir son token via /auth/refresh/	✅	✅	✅
Consulter son propre profil (/auth/me/)	✅	✅	✅
Créer un partenaire	✅	❌	❌
Lister tous les partenaires	✅	❌	❌
Consulter un partenaire spécifique	✅	❌	❌
Modifier un partenaire	✅	❌	❌
Désactiver un partenaire	✅	❌	❌
Créer un livreur	✅	❌	❌
Lister tous les livreurs	✅	❌	❌
Consulter un livreur spécifique	✅	❌	❌
Modifier un livreur	✅	❌	❌
Désactiver un livreur	✅	❌	❌
Générer une clé API	✅	❌	❌
Révoquer une clé API	✅	❌	❌
Utiliser une clé API	❌	✅	❌


Attribution des rôles
Comment un rôle est attribué
Rôle	Mode d'attribution
ADMIN	Création technique via le superutilisateur Django (hors API)
PARTENAIRE	Création via /admin/partenaires/ par un ADMIN
LIVREUR	Création via /admin/livreurs/ par un ADMIN


Règles d'attribution
Aucun rôle ne peut être auto-attribué. Un utilisateur ne peut pas se donner un rôle.

Aucun rôle ne peut être modifié après création. Pour changer de rôle, il faut créer un nouveau compte.

Un ADMIN ne peut pas créer un autre ADMIN via l'API. La création d'ADMIN reste une opération technique.

Un PARTENAIRE et un LIVREUR ne peuvent pas créer d'autres comptes.

* Permissions et mécanismes d'authentification
Les permissions s'appliquent après l'authentification. Les deux concepts sont distincts :

Étape	Question posée	Réponse en cas d'échec
Authentification	« Qui es-tu ? »	401 Unauthorized
Autorisation (permission)	« As-tu le bon rôle ? »	403 Forbidden

Permissions et mécanismes d'authentification
Les permissions s'appliquent après l'authentification. Les deux concepts sont distincts :

Étape	Question posée	Réponse en cas d'échec
Authentification	« Qui es-tu ? »	401 Unauthorized
Autorisation (permission)	« As-tu le bon rôle ? »	403 Forbidden
Exemples de combinaisons
Situation	Authentification	Permission	Résultat
Visiteur anonyme appelle /admin/partenaires/	❌	—	401
PARTENAIRE authentifié appelle /admin/partenaires/	✅	❌	403
ADMIN authentifié appelle /admin/partenaires/	✅	✅	200
LIVREUR authentifié appelle /livreur/courses/disponibles/	✅	✅	200
PARTENAIRE authentifié appelle /livreur/courses/disponibles/	✅	❌	403
ADMIN appelle /partenaire/courses/	✅	❌	403 (l'ADMIN n'a pas la permission EstPartenair)

Note importante : un ADMIN authentifié n'a pas automatiquement accès aux endpoints /partenaire/* ou /livreur/*. Chaque espace a sa propre permission.

Différence entre permission et restriction
Il est essentiel de ne pas confondre :

Concept	Question posée	Réponse en cas d'échec
Permission (autorisation)	« As-tu le bon rôle pour appeler cet endpoint ? »	403 Forbidden
Restriction (propriété)	« Cette donnée t'appartient-elle ? »	404 Not Found
Exemple concret :

Un PARTENAIRE appelle GET /partenaire/courses/ → permission OK (il a le rôle PARTENAIRE).

Le système filtre automatiquement pour ne renvoyer que ses courses.

S'il tente d'accéder à GET /partenaire/courses/{id}/ où {id} est une course d'un autre partenaire → le système renvoie 404 (pas 403, pour ne pas révéler l'existence de la course).

Cette distinction sera développée en détail dans la Partie 5 (Restriction d'accès aux données).

Règles à retenir
Trois rôles, un seul par utilisateur, fixé à la création.

Quatre permissions de base exposées par accounts et utilisées partout.

Le JWT est universel — tous les acteurs peuvent s'authentifier par ce mécanisme.

La clé API est réservée au PARTENAIRE — c'est une alternative optionnelle, en complément du JWT.

Aucun rôle ne peut être modifié après création du compte.

Un ADMIN n'a pas automatiquement accès aux endpoints /partenaire/* ou /livreur/* — chaque espace a sa propre permission.

Permission (403) ≠ Restriction (404) — la première parle de rôle, la seconde parle de
# MODULE accounts — Document de conception technique (suite)

---

# 2.5. Gestion des clés API — génération, stockage, révocation

## Rôle de la clé API

La clé API est un **mécanisme d'authentification alternatif** réservé au PARTENAIRE. Elle permet à un système externe (le backend du partenaire) d'appeler notre API **sans passer par un écran de connexion**. Elle vient **en complément** du JWT, jamais en remplacement.

## Qui peut générer une clé API

Uniquement l'**ADMIN**, via un endpoint dédié.

## Quand générer une clé API

- **Automatiquement** à la création d'un partenaire (première clé).
- **Manuellement** à la demande (régénération après perte ou compromission).

## Comment est générée la clé

- Le système produit un **secret aléatoire** de longueur suffisante (32 caractères minimum).
- Un **préfixe lisible** est ajouté pour identification visuelle (exemple : `pk_live_`).
- Le secret complet est retourné **en clair à l'ADMIN, une seule fois**.

## Ce qui est stocké en base

- Le **hash** de la clé (seul le hash est persisté).
- Le **préfixe** (portion visible, pour identification).
- La **date de création**.
- Le **statut** (active / révoquée).
- La **date de révocation** (si applicable).
- Le **lien vers le partenaire** propriétaire.

## Ce qui n'est JAMAIS stocké

- La clé en clair. Une fois affichée à l'ADMIN, elle est **irrécupérable**.

## Utilisation de la clé

1. Le partenaire envoie sa clé dans l'en-tête `X-API-Key`.
2. Le serveur hache la clé reçue.
3. Le serveur compare ce hash aux hashes stockés.
4. Si un hash correspond et que la clé est **active**, le partenaire est identifié.
5. Sinon → **401 Unauthorized**.

## Révocation

### Qui peut révoquer
Uniquement l'**ADMIN**.

### Quand révoquer
- Le partenaire signale une compromission.
- L'ADMIN régénère une clé (l'ancienne est automatiquement révoquée).
- Le partenaire est désactivé (toutes ses clés sont révoquées).

### Effet de la révocation
- **Immédiat** : la clé devient inutilisable dès la révocation.
- **Irréversible** : une clé révoquée ne peut pas être réactivée.

## Régénération

L'ADMIN peut générer une **nouvelle clé** pour un partenaire. La régénération :
- Crée une nouvelle clé active.
- Révoque automatiquement l'ancienne clé active.
- Affiche la nouvelle clé en clair **une seule fois**.

## Règles de sécurité spécifiques

- **Une seule clé active à la fois** par partenaire.
- **La clé n'est jamais loggée** dans les journaux du serveur.
- **La clé n'est jamais renvoyée** dans une réponse API après sa création initiale.
- **La comparaison de hash** doit se faire en temps constant (anti-timing attack).
- **Rate limiting** applicable aux tentatives d'authentification par clé.

---

# Partie 3 — Interfaces exposées (API)

## 3.1. Endpoints d'authentification — /auth/*

### POST /api/v1/auth/login/
- **Description** : Authentifie un utilisateur (ADMIN, PARTENAIRE ou LIVREUR) et retourne un JWT.
- **Auth requise** : Aucune (porte d'entrée)
- **Rôle autorisé** : Tous (ADMIN, PARTENAIRE, LIVREUR)
- **Restriction** : Aucune, mais un compte désactivé est refusé.

### POST /api/v1/auth/refresh/
- **Description** : Renouvelle l'access token à partir du refresh token.
- **Auth requise** : Refresh token valide (porte d'entrée)
- **Rôle autorisé** : Tous

### GET /api/v1/auth/me/
- **Description** : Retourne le profil de l'utilisateur connecté.
- **Auth requise** : JWT
- **Rôle autorisé** : Tous
- **Restriction** : L'utilisateur ne voit que **son propre** profil.

### POST /api/v1/auth/logout/
- **Description** : Invalide le refresh token (blacklist).
- **Auth requise** : JWT
- **Rôle autorisé** : Tous

---

## 3.2. Endpoints d'administration — /admin/partenaires/*, /admin/livreurs/*

### Partenaires

- `GET /api/v1/admin/partenaires/` — Lister les partenaires (ADMIN uniquement)
- `POST /api/v1/admin/partenaires/` — Créer un partenaire (ADMIN uniquement)
- `GET /api/v1/admin/partenaires/{id}/` — Détail d'un partenaire (ADMIN uniquement)
- `PATCH /api/v1/admin/partenaires/{id}/` — Modifier un partenaire (ADMIN uniquement)
- `DELETE /api/v1/admin/partenaires/{id}/` — Désactiver un partenaire (ADMIN uniquement)
- `POST /api/v1/admin/partenaires/{id}/generer-cle/` — Générer une clé API (ADMIN uniquement)
- `POST /api/v1/admin/partenaires/{id}/revoquer-cle/` — Révoquer la clé active (ADMIN uniquement)

### Livreurs

- `GET /api/v1/admin/livreurs/` — Lister les livreurs (ADMIN uniquement)
- `POST /api/v1/admin/livreurs/` — Créer un livreur (ADMIN uniquement)
- `GET /api/v1/admin/livreurs/{id}/` — Détail d'un livreur (ADMIN uniquement)
- `PATCH /api/v1/admin/livreurs/{id}/` — Modifier un livreur (ADMIN uniquement)
- `DELETE /api/v1/admin/livreurs/{id}/` — Désactiver un livreur (ADMIN uniquement)

---

## 3.3. Contrats d'entrée/sortie — format des requêtes et réponses (JSON)


### FORMA JSON DU MODELE CONCEPTUELE



### Règle générale
Toute réponse suit **exactement** ce format :

**Succès :**
```json
{
  "success": true,
  "data": { },
  "error": null
}
```
### FORMA JSON DU MODELE CONCEPTUELE
```json

{
  "module": "accounts",
  "version": "1.1",
  "description": "Modèle conceptuel de données du module accounts — Mashop Livraison. Version enrichie pour faciliter l'intégration frontend : chaque attribut précise son exposition, son format, ses contraintes et ses valeurs possibles.",
  "conventions_frontend": {
    "format_reponse_succes": {
      "success": true,
      "data": "objet ou tableau",
      "error": null
    },
    "format_reponse_erreur": {
      "success": false,
      "data": null,
      "error": {
        "code": "identifiant_technique",
        "detail": "message lisible"
      }
    },
    "format_date": "ISO 8601 (ex: 2026-10-13T14:32:00Z)",
    "format_uuid": "UUID v4 (ex: 550e8400-e29b-41d4-a716-446655440000)",
    "format_email": "RFC 5322",
    "format_telephone": "E.164 (ex: +243971000001)",
    "encodage": "UTF-8",
    "langue_messages": "français"
  },
  "enumerations": [
    {
      "nom": "Role",
      "utilise_par": ["Utilisateur.role"],
      "description": "Rôle unique attribué à un Utilisateur. Détermine son type d'accès et les endpoints accessibles.",
      "valeurs": [
        {
          "code": "ADMIN",
          "label_fr": "Administrateur",
          "description": "Accès global à toutes les données et opérations d'administration.",
          "couleur_ui": "#1E40AF",
          "icone_ui": "shield-admin",
          "espace_frontend": "/admin",
          "mecanisme_auth": "JWT uniquement",
          "permission_endpoints": ["/admin/*"]
        },
        {
          "code": "PARTENAIRE",
          "label_fr": "Partenaire",
          "description": "Boutique qui crée des demandes de livraison. Accès restreint à ses propres données.",
          "couleur_ui": "#EA580C",
          "icone_ui": "store",
          "espace_frontend": "/partenaire",
          "mecanisme_auth": "JWT ou clé API",
          "permission_endpoints": ["/partenaire/*"]
        },
        {
          "code": "LIVREUR",
          "label_fr": "Livreur",
          "description": "Personne qui effectue les livraisons. Accès restreint à ses propres courses.",
          "couleur_ui": "#16A34A",
          "icone_ui": "truck",
          "espace_frontend": "/livreur",
          "mecanisme_auth": "JWT uniquement",
          "permission_endpoints": ["/livreur/*"]
        }
      ]
    },
    {
      "nom": "EtatCompte",
      "utilise_par": ["Utilisateur.etat", "Partenaire.etat", "Livreur.etat"],
      "description": "État du cycle de vie d'un compte. Distinct des états de livraison (qui appartiennent au module courses).",
      "valeurs": [
        {
          "code": "CREE",
          "label_fr": "Créé",
          "description": "Compte créé mais pas encore activé (état transitoire très bref).",
          "couleur_ui": "#94A3B8",
          "compte_utilisable": false
        },
        {
          "code": "ACTIF",
          "label_fr": "Actif",
          "description": "Compte pleinement utilisable.",
          "couleur_ui": "#16A34A",
          "compte_utilisable": true
        },
        {
          "code": "DESACTIVE",
          "label_fr": "Désactivé",
          "description": "Compte bloqué par un ADMIN. Aucun accès possible.",
          "couleur_ui": "#DC2626",
          "compte_utilisable": false
        },
        {
          "code": "REACTIVE",
          "label_fr": "Réactivé",
          "description": "Compte précédemment désactivé et remis en service.",
          "couleur_ui": "#16A34A",
          "compte_utilisable": true
        },
        {
          "code": "SUPPRIME",
          "label_fr": "Supprimé",
          "description": "État théorique, jamais atteint si le compte a des données liées.",
          "couleur_ui": "#000000",
          "compte_utilisable": false
        }
      ],
      "transitions_autorisees": {
        "CREE": ["ACTIF"],
        "ACTIF": ["DESACTIVE"],
        "DESACTIVE": ["REACTIVE"],
        "REACTIVE": ["DESACTIVE"],
        "SUPPRIME": []
      },
      "regles": [
        "Un compte créé devient actif immédiatement (pas de validation email dans cette version).",
        "Un compte ACTIF peut être désactivé par un ADMIN.",
        "Un compte DESACTIVE peut être réactivé par un ADMIN.",
        "Un compte avec données liées (courses) ne peut jamais être SUPPRIME.",
        "Un ADMIN ne peut pas désactiver un autre ADMIN via l'API."
      ]
    },
    {
      "nom": "StatutCleAPI",
      "utilise_par": ["CleAPI.statut"],
      "description": "Statut d'une clé API. Une seule clé ACTIVE par partenaire à un instant donné.",
      "valeurs": [
        {
          "code": "ACTIVE",
          "label_fr": "Active",
          "description": "Clé utilisable pour authentifier le partenaire.",
          "couleur_ui": "#16A34A",
          "utilisable": true
        },
        {
          "code": "REVOQUEE",
          "label_fr": "Révoquée",
          "description": "Clé définitivement inutilisable.",
          "couleur_ui": "#DC2626",
          "utilisable": false
        }
      ],
      "regles": [
        "La révocation est irréversible.",
        "La génération d'une nouvelle clé révoque automatiquement l'ancienne.",
        "La désactivation d'un partenaire révoque toutes ses clés."
      ]
    },
    {
      "nom": "TypeAuthentification",
      "utilise_par": ["Tous les endpoints protégés"],
      "description": "Mécanisme utilisé pour authentifier une requête entrante.",
      "valeurs": [
        {
          "code": "JWT",
          "label_fr": "JWT",
          "description": "Token JWT dans l'en-tête Authorization.",
          "header_http": "Authorization: Bearer <access_token>",
          "acteurs": ["ADMIN", "PARTENAIRE", "LIVREUR"]
        },
        {
          "code": "CLE_API",
          "label_fr": "Clé API",
          "description": "Clé API dans un en-tête dédié.",
          "header_http": "X-API-Key: <cle>",
          "acteurs": ["PARTENAIRE"]
        },
        {
          "code": "AUCUNE",
          "label_fr": "Aucune",
          "description": "Point d'entrée d'authentification (login/refresh uniquement).",
          "acteurs": ["Tous"]
        }
      ]
    },
    {
      "nom": "NiveauAcces",
      "utilise_par": ["Permissions des endpoints"],
      "description": "Niveau d'accès requis pour appeler un endpoint.",
      "valeurs": [
        {
          "code": "PUBLIC",
          "label_fr": "Public",
          "description": "Accessible sans authentification (uniquement login/refresh)."
        },
        {
          "code": "AUTHENTIFIE",
          "label_fr": "Authentifié",
          "description": "Nécessite un JWT ou une clé API valide."
        },
        {
          "code": "ADMIN",
          "label_fr": "Administrateur",
          "description": "Nécessite le rôle ADMIN."
        },
        {
          "code": "PARTENAIRE",
          "label_fr": "Partenaire",
          "description": "Nécessite le rôle PARTENAIRE."
        },
        {
          "code": "LIVREUR",
          "label_fr": "Livreur",
          "description": "Nécessite le rôle LIVREUR."
        }
      ]
    },
    {
      "nom": "PorteeAcces",
      "utilise_par": ["Toutes les ressources"],
      "description": "Étendue des données accessibles à un utilisateur.",
      "valeurs": [
        {
          "code": "GLOBAL",
          "label_fr": "Global",
          "description": "Accès à toutes les données (réservé à l'ADMIN)."
        },
        {
          "code": "PROPRE",
          "label_fr": "Propre",
          "description": "Accès uniquement aux données dont l'utilisateur est propriétaire."
        },
        {
          "code": "AUCUN",
          "label_fr": "Aucun",
          "description": "Aucun accès (utilisé pour les visiteurs non authentifiés)."
        }
      ]
    }
  ],
  "entites": [
    {
      "nom": "Utilisateur",
      "persistee": true,
      "exposee_frontend": true,
      "description": "Identité de connexion de base. Toute personne authentifiée sur la plateforme possède un Utilisateur.",
      "endpoints_associes": [
        "POST /api/v1/auth/login/",
        "POST /api/v1/auth/refresh/",
        "POST /api/v1/auth/logout/",
        "GET  /api/v1/auth/me/"
      ],
      "attributs": [
        {
          "nom": "id",
          "type": "UUID",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "identite",
          "label_fr": "Identifiant",
          "format_affichage": "uuid",
          "exemple_valeur": "550e8400-e29b-41d4-a716-446655440000",
          "description": "Identifiant technique unique généré par le serveur."
        },
        {
          "nom": "nom",
          "type": "string",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": false,
          "nullable": false,
          "requis_creation": true,
          "requis_modification": true,
          "groupe_ui": "identite",
          "label_fr": "Nom",
          "format_affichage": "texte",
          "longueur_min": 2,
          "longueur_max": 100,
          "exemple_valeur": "CIRINDYE",
          "description": "Nom de famille de l'utilisateur."
        },
        {
          "nom": "prenom",
          "type": "string",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": false,
          "nullable": false,
          "requis_creation": true,
          "requis_modification": true,
          "groupe_ui": "identite",
          "label_fr": "Prénom",
          "format_affichage": "texte",
          "longueur_min": 2,
          "longueur_max": 100,
          "exemple_valeur": "Frederick",
          "description": "Prénom de l'utilisateur."
        },
        {
          "nom": "email",
          "type": "string",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "requis_creation": true,
          "requis_modification": false,
          "groupe_ui": "identite",
          "label_fr": "Email",
          "format_affichage": "email",
          "exemple_valeur": "admin@mashop.cd",
          "description": "Email unique, sert d'identifiant de connexion. Non modifiable après création."
        },
        {
          "nom": "telephone",
          "type": "string",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": false,
          "nullable": false,
          "requis_creation": true,
          "requis_modification": false,
          "groupe_ui": "contact",
          "label_fr": "Téléphone",
          "format_affichage": "telephone",
          "exemple_valeur": "+243971000001",
          "description": "Numéro de téléphone au format international."
        },
        {
          "nom": "mot_de_passe",
          "type": "string",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": false,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": true,
          "nullable": false,
          "requis_creation": true,
          "requis_modification": false,
          "groupe_ui": "securite",
          "label_fr": "Mot de passe",
          "format_affichage": "masque",
          "exemple_valeur": null,
          "description": "Mot de passe haché côté serveur. Jamais renvoyé dans une réponse API. Jamais loggé."
        },
        {
          "nom": "role",
          "type": "enum",
          "enum_ref": "Role",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "identite",
          "label_fr": "Rôle",
          "format_affichage": "badge",
          "exemple_valeur": "ADMIN",
          "description": "Rôle unique de l'utilisateur. Fixé à la création, non modifiable."
        },
        {
          "nom": "etat",
          "type": "enum",
          "enum_ref": "EtatCompte",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": "ACTIF",
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "statut",
          "label_fr": "État du compte",
          "format_affichage": "badge",
          "exemple_valeur": "ACTIF",
          "description": "État du cycle de vie du compte. Remplace le booléen actif."
        },
        {
          "nom": "actif",
          "type": "boolean",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": true,
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "statut",
          "label_fr": "Compte actif",
          "format_affichage": "booleen",
          "exemple_valeur": true,
          "description": "Raccourci calculé : vrai si etat est ACTIF ou REACTIVE."
        },
        {
          "nom": "date_creation",
          "type": "datetime",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "audit",
          "label_fr": "Date de création",
          "format_affichage": "date_iso",
          "exemple_valeur": "2026-10-13T14:32:00Z",
          "description": "Date de création du compte."
        },
        {
          "nom": "date_derniere_connexion",
          "type": "datetime",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": true,
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "audit",
          "label_fr": "Dernière connexion",
          "format_affichage": "date_iso",
          "exemple_valeur": "2026-10-13T14:35:22Z",
          "description": "Date de la dernière connexion réussie."
        }
      ],
      "champs_masques_frontend": ["mot_de_passe"],
      "champs_calcules": ["actif"],
      "champs_lecture_seule": ["id", "role", "etat", "actif", "date_creation", "date_derniere_connexion"],
      "champs_modifiables": ["nom", "prenom", "telephone", "mot_de_passe"],
      "contraintes": [
        "email unique dans toute la table",
        "role non modifiable après création",
        "un seul rôle par utilisateur",
        "etat ne peut transiter que selon les règles de EtatCompte"
      ]
    },
    {
      "nom": "Administrateur",
      "persistee": false,
      "exposee_frontend": false,
      "description": "Simple rôle sur l'Utilisateur. Aucune table dédiée. Aucune entité frontend distincte.",
      "endpoints_associes": [],
      "attributs": [],
      "contraintes": [
        "identifié uniquement par role = ADMIN sur Utilisateur",
        "créé hors API (via superutilisateur Django)",
        "ne peut pas désactiver un autre ADMIN via l'API",
        "non exposé comme entité indépendante au frontend"
      ]
    },
    {
      "nom": "Partenaire",
      "persistee": true,
      "exposee_frontend": true,
      "description": "Profil métier attaché à un Utilisateur de rôle PARTENAIRE. Contient les informations commerciales.",
      "endpoints_associes": [
        "GET    /api/v1/admin/partenaires/",
        "POST   /api/v1/admin/partenaires/",
        "GET    /api/v1/admin/partenaires/{id}/",
        "PATCH  /api/v1/admin/partenaires/{id}/",
        "DELETE /api/v1/admin/partenaires/{id}/",
        "POST   /api/v1/admin/partenaires/{id}/generer-cle/",
        "POST   /api/v1/admin/partenaires/{id}/revoquer-cle/"
      ],
      "attributs": [
        {
          "nom": "id",
          "type": "UUID",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "identite",
          "label_fr": "Identifiant",
          "format_affichage": "uuid",
          "description": "Identifiant technique unique du partenaire."
        },
        {
          "nom": "utilisateur_id",
          "type": "UUID",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "relation",
          "label_fr": "Utilisateur associé",
          "format_affichage": "uuid",
          "description": "Référence vers Utilisateur (relation 1-à-1)."
        },
        {
          "nom": "nom_boutique",
          "type": "string",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": false,
          "nullable": false,
          "requis_creation": true,
          "requis_modification": true,
          "groupe_ui": "commercial",
          "label_fr": "Nom de la boutique",
          "format_affichage": "texte",
          "longueur_min": 2,
          "longueur_max": 150,
          "exemple_valeur": "Kivu Shop",
          "description": "Raison sociale de la boutique. Unique parmi les partenaires actifs."
        },
        {
          "nom": "url_webhook",
          "type": "string",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": false,
          "nullable": true,
          "requis_creation": false,
          "requis_modification": false,
          "groupe_ui": "technique",
          "label_fr": "URL de webhook",
          "format_affichage": "url",
          "exemple_valeur": "https://kivushop.cd/hooks",
          "description": "URL à laquelle le système enverra les notifications de changement de statut."
        },
        {
          "nom": "etat",
          "type": "enum",
          "enum_ref": "EtatCompte",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": "ACTIF",
          "groupe_ui": "statut",
          "label_fr": "État du partenaire",
          "format_affichage": "badge",
          "exemple_valeur": "ACTIF",
          "description": "État du cycle de vie du partenaire."
        },
        {
          "nom": "actif",
          "type": "boolean",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": true,
          "groupe_ui": "statut",
          "label_fr": "Partenaire actif",
          "format_affichage": "booleen",
          "exemple_valeur": true,
          "description": "Raccourci calculé : vrai si etat est ACTIF ou REACTIVE."
        },
        {
          "nom": "nombre_courses",
          "type": "integer",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": 0,
          "groupe_ui": "statistiques",
          "label_fr": "Nombre de courses",
          "format_affichage": "nombre",
          "exemple_valeur": 12,
          "description": "Nombre total de courses créées par ce partenaire. Champ calculé, non stocké."
        },
        {
          "nom": "date_creation",
          "type": "datetime",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "audit",
          "label_fr": "Date de création",
          "format_affichage": "date_iso",
          "exemple_valeur": "2026-10-13T14:32:00Z",
          "description": "Date de création du profil partenaire."
        }
      ],
      "champs_masques_frontend": [],
      "champs_calcules": ["actif", "nombre_courses"],
      "champs_lecture_seule": ["id", "utilisateur_id", "etat", "actif", "nombre_courses", "date_creation"],
      "champs_modifiables": ["nom_boutique", "url_webhook"],
      "contraintes": [
        "utilisateur_id unique (relation 1-à-1 stricte)",
        "nom_boutique unique parmi les partenaires actifs",
        "suppression interdite si des courses existent"
      ]
    },
    {
      "nom": "Livreur",
      "persistee": true,
      "exposee_frontend": true,
      "description": "Profil métier attaché à un Utilisateur de rôle LIVREUR. Contient les informations opérationnelles.",
      "endpoints_associes": [
        "GET    /api/v1/admin/livreurs/",
        "POST   /api/v1/admin/livreurs/",
        "GET    /api/v1/admin/livreurs/{id}/",
        "PATCH  /api/v1/admin/livreurs/{id}/",
        "DELETE /api/v1/admin/livreurs/{id}/"
      ],
      "attributs": [
        {
          "nom": "id",
          "type": "UUID",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "identite",
          "label_fr": "Identifiant",
          "format_affichage": "uuid",
          "description": "Identifiant technique unique du livreur."
        },
        {
          "nom": "utilisateur_id",
          "type": "UUID",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "relation",
          "label_fr": "Utilisateur associé",
          "format_affichage": "uuid",
          "description": "Référence vers Utilisateur (relation 1-à-1)."
        },
        {
          "nom": "disponible",
          "type": "boolean",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": false,
          "modifiable": true,
          "sensible": false,
          "nullable": false,
          "defaut": false,
          "groupe_ui": "operationnel",
          "label_fr": "Disponible",
          "format_affichage": "booleen",
          "exemple_valeur": true,
          "description": "Indique si le livreur accepte de recevoir des courses."
        },
        {
          "nom": "etat",
          "type": "enum",
          "enum_ref": "EtatCompte",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": "ACTIF",
          "groupe_ui": "statut",
          "label_fr": "État du livreur",
          "format_affichage": "badge",
          "exemple_valeur": "ACTIF",
          "description": "État du cycle de vie du livreur."
        },
        {
          "nom": "actif",
          "type": "boolean",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": true,
          "groupe_ui": "statut",
          "label_fr": "Livreur actif",
          "format_affichage": "booleen",
          "exemple_valeur": true,
          "description": "Raccourci calculé : vrai si etat est ACTIF ou REACTIVE."
        },
        {
          "nom": "courses_en_cours",
          "type": "integer",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": 0,
          "groupe_ui": "statistiques",
          "label_fr": "Courses en cours",
          "format_affichage": "nombre",
          "exemple_valeur": 1,
          "description": "Nombre de courses actuellement assignées et non terminées. Champ calculé."
        },
        {
          "nom": "courses_du_jour",
          "type": "integer",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "defaut": 0,
          "groupe_ui": "statistiques",
          "label_fr": "Courses du jour",
          "format_affichage": "nombre",
          "exemple_valeur": 5,
          "description": "Nombre de courses traitées dans la journée. Champ calculé."
        },
        {
          "nom": "date_creation",
          "type": "datetime",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "audit",
          "label_fr": "Date de création",
          "format_affichage": "date_iso",
          "exemple_valeur": "2026-10-13T14:32:00Z",
          "description": "Date de création du profil livreur."
        }
      ],
      "champs_masques_frontend": [],
      "champs_calcules": ["actif", "courses_en_cours", "courses_du_jour"],
      "champs_lecture_seule": ["id", "utilisateur_id", "etat", "actif", "courses_en_cours", "courses_du_jour", "date_creation"],
      "champs_modifiables": ["disponible"],
      "contraintes": [
        "utilisateur_id unique (relation 1-à-1 stricte)",
        "suppression interdite si des courses existent",
        "avertissement requis si désactivation avec courses en cours"
      ]
    },
    {
      "nom": "CleAPI",
      "persistee": true,
      "exposee_frontend": true,
      "description": "Secret d'authentification alternatif réservé au Partenaire. Permet l'appel API serveur-à-serveur sans JWT.",
      "endpoints_associes": [
        "POST /api/v1/admin/partenaires/{id}/generer-cle/",
        "POST /api/v1/admin/partenaires/{id}/revoquer-cle/"
      ],
      "attributs": [
        {
          "nom": "id",
          "type": "UUID",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "identite",
          "label_fr": "Identifiant",
          "format_affichage": "uuid",
          "description": "Identifiant technique unique de la clé."
        },
        {
          "nom": "partenaire_id",
          "type": "UUID",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "relation",
          "label_fr": "Partenaire associé",
          "format_affichage": "uuid",
          "description": "Référence vers Partenaire (relation plusieurs-à-1)."
        },
        {
          "nom": "prefixe",
          "type": "string",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "technique",
          "label_fr": "Préfixe de la clé",
          "format_affichage": "texte",
          "exemple_valeur": "pk_live_xxxx",
          "description": "Portion visible de la clé, utilisée pour identification rapide."
        },
        {
          "nom": "valeur",
          "type": "string",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": true,
          "nullable": true,
          "groupe_ui": "securite",
          "label_fr": "Clé en clair",
          "format_affichage": "texte",
          "exemple_valeur": "pk_live_xxxxxxxxxxxxxxxxxxxxxxxx",
          "description": "Affichée UNE SEULE FOIS à la génération. Jamais renvoyée ensuite."
        },
        {
          "nom": "hash",
          "type": "string",
          "obligatoire": true,
          "unique": true,
          "expose_frontend": false,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": true,
          "nullable": false,
          "groupe_ui": "securite",
          "label_fr": "Hash de la clé",
          "format_affichage": "masque",
          "description": "Hash de la clé — JAMAIS exposé au frontend."
        },
        {
          "nom": "statut",
          "type": "enum",
          "enum_ref": "StatutCleAPI",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "statut",
          "label_fr": "Statut de la clé",
          "format_affichage": "badge",
          "exemple_valeur": "ACTIVE",
          "description": "Statut de la clé API."
        },
        {
          "nom": "date_creation",
          "type": "datetime",
          "obligatoire": true,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": false,
          "groupe_ui": "audit",
          "label_fr": "Date de génération",
          "format_affichage": "date_iso",
          "exemple_valeur": "2026-10-13T14:32:00Z",
          "description": "Date de génération de la clé."
        },
        {
          "nom": "date_revocation",
          "type": "datetime",
          "obligatoire": false,
          "unique": false,
          "expose_frontend": true,
          "lecture_seule": true,
          "modifiable": false,
          "sensible": false,
          "nullable": true,
          "groupe_ui": "audit",
          "label_fr": "Date de révocation",
          "format_affichage": "date_iso",
          "exemple_valeur": "2026-10-14T09:15:00Z",
          "description": "Date de révocation (uniquement si statut = REVOQUEE)."
        }
      ],
      "champs_masques_frontend": ["hash"],
      "champs_exposes_une_seule_fois": ["valeur"],
      "champs_calcules": [],
      "champs_lecture_seule": ["id", "partenaire_id", "prefixe", "valeur", "statut", "date_creation", "date_revocation"],
      "champs_modifiables": [],
      "contraintes": [
        "une seule clé ACTIVE par partenaire à un instant donné",
        "hash unique dans la table",
        "la clé en clair n'est jamais persistée",
        "révocation irréversible",
        "valeur exposée uniquement à la création"
      ]
    }
  ],
  "relations": [
    {
      "nom": "Utilisateur_Administrateur",
      "source": "Utilisateur",
      "cible": "Administrateur",
      "type": "specialisation_par_role",
      "cardinalite": "1-à-0..1",
      "persistee": false,
      "exposee_frontend": false,
      "description": "Un Utilisateur de rôle ADMIN est un Administrateur. Aucune entité frontend distincte."
    },
    {
      "nom": "Utilisateur_Partenaire",
      "source": "Utilisateur",
      "cible": "Partenaire",
      "type": "association_1_a_1",
      "cardinalite": "1-à-1",
      "persistee": true,
      "obligatoire": true,
      "exposee_frontend": true,
      "champ_liaison_source": "utilisateur_id",
      "description": "Un Utilisateur de rôle PARTENAIRE possède exactement un Partenaire."
    },
    {
      "nom": "Utilisateur_Livreur",
      "source": "Utilisateur",
      "cible": "Livreur",
      "type": "association_1_a_1",
      "cardinalite": "1-à-1",
      "persistee": true,
      "obligatoire": true,
      "exposee_frontend": true,
      "champ_liaison_source": "utilisateur_id",
      "description": "Un Utilisateur de rôle LIVREUR possède exactement un Livreur."
    },
    {
      "nom": "Partenaire_CleAPI",
      "source": "Partenaire",
      "cible": "CleAPI",
      "type": "association_1_a_plusieurs",
      "cardinalite": "1-à-0..N",
      "persistee": true,
      "obligatoire": false,
      "exposee_frontend": true,
      "champ_liaison_source": "partenaire_id",
      "description": "Un Partenaire peut avoir plusieurs clés au fil du temps. Une seule active à un instant donné."
    }
  ],
  "endpoints_par_acteur": {
    "ADMIN": [
      { "methode": "POST",  "url": "/api/v1/auth/login/",                              "niveau_acces": "PUBLIC",       "portee": "AUCUN" },
      { "methode": "POST",  "url": "/api/v1/auth/refresh/",                            "niveau_acces": "PUBLIC",       "portee": "AUCUN" },
      { "methode": "POST",  "url": "/api/v1/auth/logout/",                             "niveau_acces": "AUTHENTIFIE",  "portee": "PROPRE" },
      { "methode": "GET",   "url": "/api/v1/auth/me/",                                 "niveau_acces": "AUTHENTIFIE",  "portee": "PROPRE" },
      { "methode": "GET",   "url": "/api/v1/admin/partenaires/",                       "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "POST",  "url": "/api/v1/admin/partenaires/",                       "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "GET",   "url": "/api/v1/admin/partenaires/{id}/",                  "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "PATCH", "url": "/api/v1/admin/partenaires/{id}/",                  "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "DELETE","url": "/api/v1/admin/partenaires/{id}/",                  "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "POST",  "url": "/api/v1/admin/partenaires/{id}/generer-cle/",      "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "POST",  "url": "/api/v1/admin/partenaires/{id}/revoquer-cle/",     "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "GET",   "url": "/api/v1/admin/livreurs/",                          "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "POST",  "url": "/api/v1/admin/livreurs/",                          "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "GET",   "url": "/api/v1/admin/livreurs/{id}/",                     "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "PATCH", "url": "/api/v1/admin/livreurs/{id}/",                     "niveau_acces": "ADMIN",        "portee": "GLOBAL" },
      { "methode": "DELETE","url": "/api/v1/admin/livreurs/{id}/",                     "niveau_acces": "ADMIN",        "portee": "GLOBAL" }
    ],
    "PARTENAIRE": [
      { "methode": "POST",  "url": "/api/v1/auth/login/",                              "niveau_acces": "PUBLIC",       "portee": "AUCUN" },
      { "methode": "POST",  "url": "/api/v1/auth/refresh/",                            "niveau_acces": "PUBLIC",       "portee": "AUCUN" },
      { "methode": "POST",  "url": "/api/v1/auth/logout/",                             "niveau_acces": "AUTHENTIFIE",  "portee": "PROPRE" },
      { "methode": "GET",   "url": "/api/v1/auth/me/",                                 "niveau_acces": "AUTHENTIFIE",  "portee": "PROPRE" }
    ],
    "LIVREUR": [
      { "methode": "POST",  "url": "/api/v1/auth/login/",                              "niveau_acces": "PUBLIC",       "portee": "AUCUN" },
      { "methode": "POST",  "url": "/api/v1/auth/refresh/",                            "niveau_acces": "PUBLIC",       "portee": "AUCUN" },
      { "methode": "POST",  "url": "/api/v1/auth/logout/",                             "niveau_acces": "AUTHENTIFIE",  "portee": "PROPRE" },
      { "methode": "GET",   "url": "/api/v1/auth/me/",                                 "niveau_acces": "AUTHENTIFIE",  "portee": "PROPRE" }
    ]
  },
  "codes_erreur": [
    { "code": "invalid_credentials",             "http": 401, "detail": "Email ou mot de passe incorrect." },
    { "code": "account_disabled",                "http": 403, "detail": "Ce compte a été désactivé." },
    { "code": "token_expired",                   "http": 401, "detail": "Le token a expiré." },
    { "code": "token_invalid",                   "http": 401, "detail": "Le token est invalide." },
    { "code": "refresh_token_revoked",           "http": 401, "detail": "Le refresh token a été révoqué." },
    { "code": "api_key_invalid",                 "http": 401, "detail": "Clé API invalide." },
    { "code": "api_key_revoked",                 "http": 401, "detail": "Clé API révoquée." },
    { "code": "email_already_exists",            "http": 400, "detail": "Cet email est déjà utilisé." },
    { "code": "nom_boutique_duplicate",          "http": 400, "detail": "Ce nom de boutique est déjà pris." },
    { "code": "cannot_delete_with_courses",      "http": 400, "detail": "Suppression impossible : des courses sont liées." },
    { "code": "cannot_deactivate_admin",         "http": 403, "detail": "Impossible de désactiver un autre administrateur." },
    { "code": "cannot_generate_key_for_disabled","http": 400, "detail": "Génération impossible sur un partenaire désactivé." },
    { "code": "password_too_weak",               "http": 400, "detail": "Le mot de passe est trop faible." },
    { "code": "required_field_missing",          "http": 400, "detail": "Un champ obligatoire est manquant." },
    { "code": "forbidden",                       "http": 403, "detail": "Rôle insuffisant pour cet endpoint." },
    { "code": "not_found",                       "http": 404, "detail": "Ressource inexistante ou non accessible." }
  ],
  "regles_globales": [
    "Un Utilisateur a un seul et unique rôle, fixé à la création.",
    "Le rôle ne peut pas être modifié via l'API.",
    "Aucun compte ne peut être supprimé s'il a des données métier liées (courses).",
    "La désactivation remplace la suppression.",
    "Un ADMIN ne peut pas désactiver un autre ADMIN via l'API.",
    "La désactivation d'un partenaire révoque automatiquement toutes ses clés API.",
    "La réactivation d'un partenaire ne réactive pas les clés API révoquées.",
    "L'email est unique dans toute la table Utilisateur.",
    "Le nom de boutique est unique parmi les partenaires actifs.",
    "La clé API n'est jamais stockée en clair, seulement son hash.",
    "Les états de compte (EtatCompte) sont distincts des états de livraison (StatutCourse).",
    "Tout champ sensible (mot_de_passe, hash, valeur de clé) n'est jamais exposé sauf valeur de clé à la création.",
    "Tout endpoint protégé retourne 401 sans token, 403 avec rôle insuffisant, 404 pour une ressource non possédée."
  ]
}

```
# MODULE accounts — Liste complète des endpoints

## Convention de lecture

- 🔑 = fonctionne avec **clé API** (en plus du JWT)
- 🎫 = fonctionne **uniquement avec JWT**
- 🚪 = **porte d'entrée** (aucune authentification préalable requise)

---

## 1. Espace `/api/v1/auth/` — Authentification et profil

### 🚪 POST /api/v1/auth/login/
**Description** : Authentifie un utilisateur avec email + mot de passe. Retourne un access token, un refresh token et les informations de profil.

**Auth** : Aucune (porte d'entrée)
**Acteurs autorisés** : ADMIN, PARTENAIRE, LIVREUR
**Restriction** : Un compte avec état `DESACTIVE` est refusé (403).

---

### 🚪 POST /api/v1/auth/refresh/
**Description** : Renouvelle l'access token à partir d'un refresh token valide.

**Auth** : Refresh token (porte d'entrée)
**Acteurs autorisés** : ADMIN, PARTENAIRE, LIVREUR
**Restriction** : Un refresh token révoqué (après logout) est refusé.

---

### 🎫 POST /api/v1/auth/logout/
**Description** : Invalide le refresh token courant (blacklist côté serveur).

**Auth** : JWT
**Acteurs autorisés** : ADMIN, PARTENAIRE, LIVREUR
**Restriction** : L'utilisateur ne peut révoquer que **son propre** refresh token.

---

### 🔑 GET /api/v1/auth/me/
**Description** : Retourne le profil complet de l'utilisateur authentifié (identité, rôle, état, données du profil métier attaché).

**Auth** : **JWT ou clé API** 🔑
**Acteurs autorisés** : ADMIN, PARTENAIRE, LIVREUR
**Restriction** : L'utilisateur ne voit que **son propre** profil. Aucun paramètre `{id}` n'est accepté.

> **Pourquoi 🔑 ici ?** Un partenaire peut vérifier depuis son propre backend que sa clé API est valide et récupérer ses informations sans passer par un login.

---

## 2. Espace `/api/v1/admin/partenaires/` — Gestion des partenaires

### 🎫 GET /api/v1/admin/partenaires/
**Description** : Liste tous les partenaires de la plateforme, avec pagination et filtres (état, nom de boutique, date de création).

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global. Un PARTENAIRE reçoit 403.

---

### 🎫 POST /api/v1/admin/partenaires/
**Description** : Crée un nouveau partenaire. Crée simultanément l'Utilisateur associé (rôle PARTENAIRE) et génère une première clé API affichée **une seule fois** dans la réponse.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Email et nom de boutique uniques.

---

### 🎫 GET /api/v1/admin/partenaires/{id}/
**Description** : Détail complet d'un partenaire (identité, boutique, URL webhook, état, statistiques, liste de ses clés API).

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global.

---

### 🎫 PATCH /api/v1/admin/partenaires/{id}/
**Description** : Modifie un partenaire (nom, prénom, téléphone, nom de boutique, URL webhook). L'email et le rôle ne sont **pas modifiables**.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global.

---

### 🎫 DELETE /api/v1/admin/partenaires/{id}/
**Description** : Désactive un partenaire. La suppression physique est **interdite** si le partenaire a des courses existantes. Révoque automatiquement toutes ses clés API.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global. Un avertissement est requis si des courses sont en cours.

---

### 🎫 POST /api/v1/admin/partenaires/{id}/generer-cle/
**Description** : Génère une nouvelle clé API pour le partenaire. Révoque automatiquement la clé active précédente. La clé en clair est affichée **une seule fois** dans la réponse.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Impossible sur un partenaire désactivé (400).

---

### 🎫 POST /api/v1/admin/partenaires/{id}/revoquer-cle/
**Description** : Révoque la clé API active du partenaire. La révocation est **immédiate** et **irréversible**.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global.

---

## 3. Espace `/api/v1/admin/livreurs/` — Gestion des livreurs

### 🎫 GET /api/v1/admin/livreurs/
**Description** : Liste tous les livreurs de la plateforme, avec pagination et filtres (état, disponibilité, date de création).

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global. Un PARTENAIRE ou LIVREUR reçoit 403.

---

### 🎫 POST /api/v1/admin/livreurs/
**Description** : Crée un nouveau livreur. Crée simultanément l'Utilisateur associé (rôle LIVREUR). Le livreur est créé avec `disponible = false`.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Email unique.

---

### 🎫 GET /api/v1/admin/livreurs/{id}/
**Description** : Détail complet d'un livreur (identité, disponibilité, état, statistiques de courses).

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global.

---

### 🎫 PATCH /api/v1/admin/livreurs/{id}/
**Description** : Modifie un livreur (nom, prénom, téléphone). L'email et le rôle ne sont **pas modifiables**.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Accès global.

---

### 🎫 DELETE /api/v1/admin/livreurs/{id}/
**Description** : Désactive un livreur. La suppression physique est **interdite** si le livreur a des courses existantes.

**Auth** : JWT
**Acteurs autorisés** : ADMIN uniquement
**Restriction** : Un avertissement est requis si le livreur a des courses en cours.

---

## Tableau récapitulatif complet

| Méthode | URL | Auth | Acteurs | 🔑 clé API | Portée |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/login/` | 🚪 Aucune | Tous | ❌ | — |
| POST | `/api/v1/auth/refresh/` | 🚪 Refresh | Tous | ❌ | — |
| POST | `/api/v1/auth/logout/` | 🎫 JWT | Tous | ❌ | Propre |
| GET | `/api/v1/auth/me/` | 🔑 JWT ou clé | Tous | ✅ | Propre |
| GET | `/api/v1/admin/partenaires/` | 🎫 JWT | ADMIN | ❌ | Global |
| POST | `/api/v1/admin/partenaires/` | 🎫 JWT | ADMIN | ❌ | Global |
| GET | `/api/v1/admin/partenaires/{id}/` | 🎫 JWT | ADMIN | ❌ | Global |
| PATCH | `/api/v1/admin/partenaires/{id}/` | 🎫 JWT | ADMIN | ❌ | Global |
| DELETE | `/api/v1/admin/partenaires/{id}/` | 🎫 JWT | ADMIN | ❌ | Global |
| POST | `/api/v1/admin/partenaires/{id}/generer-cle/` | 🎫 JWT | ADMIN | ❌ | Global |
| POST | `/api/v1/admin/partenaires/{id}/revoquer-cle/` | 🎫 JWT | ADMIN | ❌ | Global |
| GET | `/api/v1/admin/livreurs/` | 🎫 JWT | ADMIN | ❌ | Global |
| POST | `/api/v1/admin/livreurs/` | 🎫 JWT | ADMIN | ❌ | Global |
| GET | `/api/v1/admin/livreurs/{id}/` | 🎫 JWT | ADMIN | ❌ | Global |
| PATCH | `/api/v1/admin/livreurs/{id}/` | 🎫 JWT | ADMIN | ❌ | Global |
| DELETE | `/api/v1/admin/livreurs/{id}/` | 🎫 JWT | ADMIN | ❌ | Global |

---

## Récapitulatif — Endpoints compatibles clé API 🔑

Dans le module `accounts`, **un seul endpoint** accepte la clé API en plus du JWT :

| Endpoint | Raison |
|---|---|
| `GET /api/v1/auth/me/` | Permet au partenaire de vérifier depuis son backend que sa clé fonctionne et de récupérer son profil sans passer par un login |

> **Note importante** : dans les autres modules (`partners` notamment), tous les endpoints `/api/v1/partenaire/*` accepteront **les deux mécanismes** (JWT et clé API). Ce n'est pas le cas dans `accounts`, où seul `/auth/me/` est concerné.

---

## Récapitulatif — Endpoints à ne PAS confondre

| Confusion fréquente | Réalité |
|---|---|
| « `/auth/me/` permet de voir n'importe quel utilisateur » | Non — uniquement son propre profil |
| « L'ADMIN peut tout faire via clé API » | Non — la clé API est réservée au partenaire |
| « Le PARTENAIRE peut lister tous les partenaires » | Non — réservé à l'ADMIN (403) |
| « La suppression physique existe » | Non — remplacée par désactivation si données liées |
| « L'email est modifiable » | Non — l'email est fixé à la création |
| « Le rôle est modifiable » | Non — fixé à la création |
