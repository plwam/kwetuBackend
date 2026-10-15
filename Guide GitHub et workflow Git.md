# MASHOP LIVRAISON — Guide GitHub et workflow Git

> Document de référence pour toute l'équipe.  
> À lire avant de faire le moindre `git push`.  
> Ce document explique **comment configurer le repo vierge** et **comment travailler chaque jour** sans casser le travail des autres.

---

## Sommaire

1. Configuration initiale du repo GitHub (une seule fois)
2. Comprendre le modèle de branches
3. Configuration Git sur chaque machine (une seule fois par personne)
4. Workflow quotidien — les 7 étapes
5. Les commandes Git de référence
6. Résolution de conflits
7. Règles d'urgence (rollback, annulation)
8. Checklist avant chaque push

---

# 1. Configuration initiale du repo GitHub (une seule fois)

Cette section est à réaliser **par une seule personne** (le chef d'équipe ou le premier disponible). Une fois terminée, les autres suivront la section 3.

## 1.1. Créer le repo sur GitHub

1. Aller sur **https://github.com** et se connecter.
2. Cliquer sur le bouton **"New repository"**.
3. Remplir :
   - **Repository name** : `mashop-delivery` (en minuscules, tirets)
   - **Description** : `Plateforme de livraison — Backend Django + Frontend React`
   - **Visibility** : `Private` (obligatoire — le code n'est pas open source)
   - **Initialize this repository with** : cocher **aucune** case (pas de README, pas de .gitignore, pas de license)
4. Cliquer sur **"Create repository"**.

## 1.2. Inviter les 4 autres membres

1. Aller dans **Settings** → **Collaborators and teams**.
2. Cliquer sur **"Add people"**.
3. Entrer le nom d'utilisateur GitHub ou l'email de chaque membre.
4. Rôle : **Write** (pas Admin — seul le chef est Admin).
5. Chaque invité recevra un email — il doit **accepter l'invitation**.

## 1.3. Protéger la branche `main`

Cette étape empêche qu'un membre push directement sur `main` et casse tout.

1. Aller dans **Settings** → **Branches**.
2. Cliquer sur **"Add branch protection rule"**.
3. **Branch name pattern** : `main`.
4. Cocher :
   - ☑ **Require a pull request before merging**
   - ☑ **Require approvals** → mettre **1**
   - ☑ **Dismiss stale pull request approvals when new commits are pushed**
   - ☑ **Require status checks to pass before merging** (une fois la CI en place)
5. Cliquer sur **"Create"**.

Répéter la même procédure pour la branche `develop` (à créer en 1.4).

## 1.4. Créer la branche `develop`

Une fois le repo cloné en local (voir section 3), faire :

```bash
git checkout -b develop
git push -u origin develop
```

1.5. Créer le fichier .gitignore
À la racine du projet :

text
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/

# Django
*.log
db.sqlite3
db.sqlite3-journal
/media/
/staticfiles/

# Environnement
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Tests
.coverage
htmlcov/
.pytest_cache/

1.5. Créer le fichier .gitignore
À la racine du projet :

text
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/

# Django
*.log
db.sqlite3
db.sqlite3-journal
/media/
/staticfiles/

# Environnement
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Tests
.coverage
htmlcov/
.pytest_cache/

# 1.7. Premier commit
```bash
git add .gitignore .env.example README.md
git commit -m "chore: initialisation du projet"
git push origin main
Puis :
```
puis.
```bash
git checkout develop
git push -u origin develop
``` 

2. Comprendre le modèle de branches
Notre projet utilise 3 niveaux de branches :

text
main        ← version stable, prête à déployer (jamais touchée directement)
  ▲
  │ (merge uniquement via PR depuis develop)
  │
develop     ← intégration en cours (jamais touchée directement)
  ▲
  │ (merge uniquement via PR depuis feature/*)
  │
feature/*   ← une branche par fonctionnalité et par personne
fix/*       ← une branche par correction de bug
chore/*     ← maintenance (dépendances, config)
# Exemple concret — Je travaille sur le login de accounts
Je vais te montrer exactement ce que tu fais, étape par étape, du début à la fin.

Contexte
Tu es Personne 1. Tu dois coder l'endpoint :

text
POST /api/v1/auth/login/
C'est un endpoint interne à ton app accounts. Personne d'autre n'y touche. Donc workflow simple : tu travailles directement sur develop.

Étape 0 — Avant de commencer (une seule fois par jour)
Tu ouvres ton terminal et tu te mets à jour :

bash
git checkout develop
git pull origin develop
Ce que ça fait : tu récupères tout ce que les autres ont poussé depuis hier.

Étape 1 — Tu vérifies ta branche
bash
git branch
Tu dois voir :

text
* develop
  main
L'étoile * indique que tu es sur develop. Parfait.

Si tu n'es pas sur develop, refais :

bash
git checkout develop
Étape 2 — Tu travailles dans ton app
Tu crées/modifies les fichiers uniquement dans apps/accounts/ :

apps/accounts/models.py (si besoin)

apps/accounts/serializers.py (le LoginSerializer)

apps/accounts/views.py (le LoginView)

apps/accounts/urls.py (la route /auth/login/)

apps/accounts/services.py (la logique de vérification)

apps/accounts/tests/test_views.py (les tests)

Tu codes pendant 1h, 2h, une journée... peu importe.

Étape 3 — Tu vérifies ce que tu as modifié
bash
git status
Tu dois voir quelque chose comme :

text
On branch develop
Your branch is up to date with 'origin/develop'.

Changes not staged for commit:
  modified:   apps/accounts/serializers.py
  modified:   apps/accounts/views.py
  modified:   apps/accounts/urls.py

Untracked files:
  apps/accounts/tests/test_login.py
Vérifie bien que tous les fichiers sont dans apps/accounts/.
Si tu vois un fichier ailleurs (ex: config/urls.py), STOP — tu dois utiliser une branche feature/* (voir section plus bas).

Étape 4 — Tu lances les vérifications avant de commiter
4.1 — Vérifier que Django ne râle pas
bash
python manage.py check
Si tu vois System check identified no issues, c'est bon.

4.2 — Vérifier que tes tests passent
bash
pytest apps/accounts/
Tous les tests doivent passer. Si un test échoue, corrige-le avant de continuer.

Étape 5 — Tu ajoutes tes fichiers
bash
git add apps/accounts/
Ce que ça fait : tu prépares tous les fichiers de ton app pour le commit.

Vérifie avec :

bash
git status
Tu dois voir tes fichiers en vert sous Changes to be committed:.

⚠️ Si tu vois un fichier .env ou db.sqlite3 dans la liste, retire-le :

```bash
git reset HEAD .env
git reset HEAD db.sqlite3
Étape 6 — Tu fais ton commit
bash
git commit -m "feat(accounts): ajout endpoint login avec JWT"
```
Structure du message :

Partie	Signification
feat	Type de changement (nouvelle fonctionnalité)
(accounts)	L'app concernée
ajout endpoint login avec JWT	Description courte, claire
Résultat :

text
[develop abc1234] feat(accounts): ajout endpoint login avec JWT
 4 files changed, 120 insertions(+), 5 deletions(-)
Étape 7 — Tu te remets à jour (AVANT de pusher)
C'est le point important. Pendant que tu codais, un autre a peut-être poussé sur develop.

```bash
git pull origin develop
3 cas possibles :

Cas A — Pas de changement
text
Already up to date.
→ Tu passes à l'étape 8.

Cas B — Changements récupérés automatiquement
text
Updating abc1234..def5678
Fast-forward
 apps/courses/views.py | 10 +++++-----
 1 file changed, 5 insertions(+), 5 deletions(-)
→ Git a fusionné automatiquement. Parfait. Tu passes à l'étape 8.

Cas C — Conflit
text
CONFLICT (content): Merge conflict in apps/accounts/urls.py
Automatic merge failed; fix conflicts and then commit the result.
→ Un autre a modifié le même fichier que toi. Tu dois résoudre le conflit (voir section "Résolution de conflits" ci-dessous).

Étape 8 — Tu pushes
```bash
git push origin develop
Résultat :

text
Enumerating objects: 8, done.
```bash
To https://github.com/organisation/mashop-delivery.git
   abc1234..xyz9999  develop -> develop

C'est fini. Ton login est sur GitHub, tout le monde peut le récupérer.
```
Récapitulatif des 8 étapes
```bash
# 1. Se mettre à jour
git checkout develop
git pull origin develop

# 2. Travailler dans apps/accounts/

# 3. Vérifier
git status

# 4. Vérifier que ça compile et que ça passe
python manage.py check
pytest apps/accounts/

# 5. Ajouter
git add apps/accounts/

# 6. Commiter
git commit -m "feat(accounts): ajout endpoint login avec JWT"

# 7. Se remettre à jour
git pull origin develop

# 8. Pousser
git push origin develop
Résolution de conflits (si étape 7 → cas C)
Si tu vois un conflit, ouvre le fichier mentionné. Tu vas trouver des marqueurs comme ceci :

python
<<<<<<< HEAD
urlpatterns = [
    path('auth/login/', LoginView.as_view()),
]
=======
urlpatterns = [
    path('auth/login/', LoginView.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
]
>>>>>>> def5678
Signification :
```
```bash
Entre <<<<<<< HEAD et ======= : ta version

Entre ======= et >>>>>>> def5678 : la version de l'autre
```

Tu choisis :

Si tu gardes ta version → supprime les marqueurs et la version de l'autre.

Si tu gardes la version de l'autre → supprime les marqueurs et ta version.

Si tu veux les deux → fusionne manuellement.

Exemple de résolution (garder les deux routes) :

```python
urlpatterns = [
    path('auth/login/', LoginView.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
]
```
Puis :

```bash
git add apps/accounts/urls.py
git commit -m "fix(accounts): résolution conflit urls"
git push origin develop
```

# Quand utiliser une branche feature/* à la place
Si tu dois modifier un fichier partagé (pas dans apps/accounts/) :

Exemple : tu dois ajouter /auth/login/ dans config/urls.py.

```bash
# 1. Se mettre à jour
git checkout develop
git pull origin develop

# 2. Créer une branche
git checkout -b feature/accounts-route-login

# 3. Travailler
# ... modifier config/urls.py et apps/accounts/ ...

# 4. Vérifier
git status
python manage.py check

# 5. Commiter
git add config/urls.py apps/accounts/
git commit -m "feat(accounts): ajout route login dans urls globales"

# 6. Pousser la branche (PAS develop)
git push -u origin feature/accounts-route-login

# 7. Sur GitHub : ouvrir une Pull Request vers develop
# 8. Attendre qu'un autre approuve
# 9. Merger la PR
# 10. Supprimer la branche
Pourquoi cette différence ?
Parce que config/urls.py est partagé. Si tu le modifies en même temps qu'un autre, il faut une review avant de merger.