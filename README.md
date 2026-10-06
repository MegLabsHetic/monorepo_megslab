# MegsLab

Plateforme d'analyse de donnees pilotee en francais. On connecte ses sources
(bases de donnees, fichiers, connecteurs Airbyte), on pose ses questions en
langage naturel, et on obtient des reponses verifiables : le SQL execute, le
resultat brut, le graphique, et ce que chaque reponse a coute.

## Ce que fait le produit

- **Sources** : PostgreSQL, MySQL, SQL Server, depot de CSV/XLSX, adoption de
  n'importe quelle source configuree dans Airbyte. Synchronisation manuelle ou
  planifiee (Airbyte), fraicheur, rapport de sante des tables, suppression propre.
- **Assistant a six agents** : Orchestrateur, Data (decrit l'entrepot, sans
  modele), Analyste (question -> SQL, derriere un garde-fou syntaxique), ML
  (regression, anomalies, projection, sans modele), Redacteur, Viz. Fils de
  conversation avec memoire, explication de la requete, avis sur chaque reponse.
- **Tableaux de bord** : des reponses epinglees dont les requetes sont rejouees
  a chaque ouverture. Exports CSV et SVG.
- **Organisation, espaces, roles** : une organisation, des espaces de travail
  isoles (un workspace Airbyte et un schema d'entrepot chacun), des roles a deux
  niveaux, invitations par lien, comptes crees par l'admin, journal d'audit,
  notifications.
- **FinOps** : cout mesure par question et par agent, budget mensuel applique
  par le code (alerte puis blocage), rapport par jour, espace, utilisateur et
  agent, part du cache de prompt, export chargeback, poids de l'entrepot.
- **Console operateur** : toutes les organisations, sante reelle d'Airbyte, de
  l'entrepot et du modele.
- **Jeu de demonstration** : un clic copie le jeu Olist dans un espace, cote
  Postgres, en quelques secondes.

## Demarrage

```bash
cp .env.example .env      # renseigner les acces Airbyte, l'entrepot et la cle du modele
docker compose up --build # front :3001 - back :8000 - swagger :8000/docs
# le port 3000 est remappe en 3001 car un autre service (Grafana) occupe deja le 3000 en local
```

Base applicative : SQLite par defaut (`backend/data/megslab.db`), migrations Alembic.

```bash
cd backend && alembic upgrade head
```

## Commandes

```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
cd backend && pytest                  # les tests d'integration sont exclus par defaut
cd backend && pytest -m integration   # exige le tunnel de lecture ci-dessous
cd backend && ruff check . && black --check .
cd frontend && npm install
cd frontend && npm run lint && npm run format:check && npx tsc --noEmit
cd frontend && npm run build
```

La CI (GitHub Actions, `.github/workflows/ci.yml`) rejoue exactement ces
commandes sur chaque push et pull request, sans aucun service externe.

### Scripts d'administration

```bash
# Donner (ou retirer, avec --retirer) le role d'operateur de la plateforme
cd backend && python -m app.scripts.promouvoir_super_admin ada@example.com

# Preparer le schema de demonstration a partir de tables deja synchronisees,
# puis renseigner DEMO_SCHEMA dans le .env
cd backend && python -m app.scripts.preparer_demo org_<id> <prefixe_> demo_olist
```

## Entrepot de donnees

Les bases Postgres (source de demonstration et entrepot) tournent sur le serveur,
sur le reseau Docker interne du cluster Airbyte. **Aucun port n'est publie** : elles
sont injoignables depuis Internet, et c'est voulu.

Pour que le backend local puisse lire l'entrepot, ouvrir un tunnel le temps du
developpement :

```bash
ssh -N -L 55433:<ip de l entrepot>:5432 <serveur>
```

Une fois le backend deploye a cote de l'entrepot, le tunnel disparait : seules
les variables `WAREHOUSE_LECTURE_*` changent.

Le moteur de lecture (DuckDB) attache l'entrepot en lecture seule, restreint au
schema de l'espace, avec l'acces fichier et reseau coupe. Le SQL du modele est
valide et regenere depuis son arbre syntaxique avant d'atteindre le moteur.

## Structure

```
backend/
  app/agents/     les six agents et leur orchestration
  app/api/        routes FastAPI, scopees par espace de travail
  app/core/       config, client Airbyte, moteur DuckDB, garde-fou SQL, ecriture entrepot
  app/models/     modeles SQLAlchemy
  app/services/   logique metier, une classe par responsabilite
  app/scripts/    scripts d'administration
  alembic/        migrations
  tests/          tests unitaires (doublures pour le modele et l'entrepot) et d'integration
frontend/
  src/app/        pages Next.js (App Router)
  src/components/ composants par domaine
  src/lib/        client API type, session, helpers
```
