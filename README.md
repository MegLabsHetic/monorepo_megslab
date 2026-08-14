# MegLabs

Plateforme d'analyse de donnees pilotee en francais. On connecte ses sources
(fichiers, bases de donnees), on pose ses questions en langage naturel, et on
obtient des analyses sans ecrire de SQL.

## Demarrage

```bash
cp .env.example .env      # renseigner au moins une cle de fournisseur LLM
docker compose up --build # front :3001 - back :8000 - swagger :8000/docs
# le port 3000 est remappe en 3001 car un autre service (Grafana) occupe deja le 3000 en local
```

## Commandes

```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
cd backend && pytest                  # les tests d'integration sont exclus par defaut
cd backend && pytest -m integration   # exige le tunnel de lecture ci-dessous
cd backend && ruff check . && black --check .
cd frontend && npm install
cd frontend && npm run lint
cd frontend && npm run build
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

## Structure

```
backend/    API FastAPI, connecteurs de donnees, agents IA
frontend/   Interface Next.js
```
