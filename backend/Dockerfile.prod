# --- Etape 1 : les dependances, isolees pour ne pas etre reconstruites -------
# Elles changent rarement, le code a chaque commit : les separer garde le cache
# de build utile sur la seule couche couteuse.
FROM python:3.12-slim AS dependances

WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Etape 2 : l'image reellement servie ------------------------------------
FROM python:3.12-slim

# curl sert au healthcheck ; ca-certificates sert a DuckDB, qui telecharge son
# extension postgres en HTTPS. Sans certificats, l'attache echoue sur un message
# qui ne dit pas pourquoi.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 megslab

COPY --from=dependances /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --chown=megslab:megslab . .

USER megslab

# Les extensions DuckDB sont telechargees ici, une fois, dans le HOME de
# l'utilisateur qui les lira. Sinon chaque conteneur neuf les retelecharge au
# premier import de fichier — et echoue si le reseau sortant est ferme.
RUN python -c "import duckdb; c = duckdb.connect(); c.execute('INSTALL postgres'); c.execute('INSTALL excel')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Pas de --reload : il surveille le disque et redemarre le processus, ce qui n'a
# aucun sens sans volume monte et coute de la memoire.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
