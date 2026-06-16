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
cd backend && pytest -q -m "not integration"
cd backend && ruff check . && black --check .
cd frontend && npm install
cd frontend && npm run lint
cd frontend && npm run build
```

## Structure

```
backend/    API FastAPI, connecteurs de donnees, agents IA
frontend/   Interface Next.js
```
