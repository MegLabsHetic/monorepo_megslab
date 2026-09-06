# --- Etape 1 : les dependances ----------------------------------------------
FROM node:20-slim AS dependances

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Etape 2 : la construction ----------------------------------------------
FROM node:20-slim AS construction

WORKDIR /app
COPY --from=dependances /app/node_modules ./node_modules
COPY . .

# ATTENTION : les variables NEXT_PUBLIC_* sont figees ICI, pas au demarrage du
# conteneur. Elles finissent dans le JavaScript envoye au navigateur, donc
# changer d'URL d'API impose de reconstruire l'image, pas de la redemarrer.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --- Etape 3 : l'image reellement servie ------------------------------------
FROM node:20-slim

ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1

RUN useradd --create-home --uid 10001 megslab
WORKDIR /app

# La sortie « standalone » embarque son propre serveur et les seules dependances
# reellement importees. Les fichiers statiques et publics restent a cote : Next
# ne les copie volontairement pas, ils sont servis tels quels.
COPY --from=construction --chown=megslab:megslab /app/.next/standalone ./
COPY --from=construction --chown=megslab:megslab /app/.next/static ./.next/static
COPY --from=construction --chown=megslab:megslab /app/public ./public

USER megslab
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
