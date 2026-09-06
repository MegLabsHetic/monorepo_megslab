"""Client pour l'API publique d'Airbyte : authentification, sources, destinations,
connexions et synchronisations.

Ne connait que le protocole HTTP d'Airbyte. La decision de quand creer quoi (et
quoi faire si Airbyte est injoignable) appartient a l'appelant.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import httpx

from app.core.config import get_settings

MARGE_EXPIRATION = timedelta(seconds=60)

# Le httpx par defaut (5s) suffit pour l'auth, mais decouverte et sync lancent
# un vrai pod Kubernetes derriere chaque appel : ca peut prendre plus d'une
# minute au demarrage a froid. Constate en pratique (ReadTimeout a 5s).
DELAI_APPEL_SECONDES = 120


@dataclass(frozen=True)
class SourceAirbyte:
    """Une source telle qu'Airbyte la connait, qu'elle vienne de MegsLab ou non."""

    id: str
    nom: str
    type_source: str


@dataclass(frozen=True)
class StreamDecouvert:
    """Une table trouvee par Airbyte lors de la decouverte du schema d'une source."""

    nom: str
    namespace: str
    colonnes: list[str]


class AirbyteClient:
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http or httpx.AsyncClient(timeout=DELAI_APPEL_SECONDES)
        self._jeton: str | None = None
        self._expire_le: datetime | None = None

    # --- Workspaces --------------------------------------------------------

    async def creer_workspace(self, nom: str) -> str:
        """Cree un workspace Airbyte et renvoie son id."""
        corps = await self._appeler("POST", "/api/public/v1/workspaces", json={"name": nom})
        return corps["workspaceId"]

    # --- Sources -------------------------------------------------------------

    async def creer_source(self, workspace_id: str, nom: str, configuration: dict) -> str:
        """Cree une source a partir d'une configuration deja formee.

        La forme exacte depend du type de base : c'est `app.core.connecteurs`
        qui la construit, pas ce client, dont le role s'arrete au transport.
        """
        corps = await self._appeler(
            "POST",
            "/api/public/v1/sources",
            json={"name": nom, "workspaceId": workspace_id, "configuration": configuration},
        )
        return corps["sourceId"]

    async def lister_sources(self, workspace_id: str) -> list[SourceAirbyte]:
        """Toutes les sources d'un workspace, y compris celles creees hors MegsLab.

        C'est ce qui permet d'adopter une source configuree directement dans
        Airbyte — et donc d'atteindre n'importe lequel de ses connecteurs, meme
        ceux que notre formulaire ne sait pas remplir.
        """
        corps = await self._appeler(
            "GET", "/api/public/v1/sources", params={"workspaceIds": workspace_id}
        )
        return [
            SourceAirbyte(
                id=source["sourceId"],
                nom=source.get("name", "Source sans nom"),
                type_source=source.get("sourceType", "inconnu"),
            )
            for source in corps.get("data", [])
        ]

    async def lister_streams(self, source_id: str) -> list[StreamDecouvert]:
        """Decouvre les tables et colonnes visibles par une source deja creee."""
        corps = await self._appeler("GET", "/api/public/v1/streams", params={"sourceId": source_id})
        return [
            StreamDecouvert(
                nom=flux["streamName"],
                namespace=flux["streamnamespace"],
                colonnes=[champ[0] for champ in flux.get("propertyFields", []) if champ],
            )
            for flux in corps
        ]

    # --- Destinations --------------------------------------------------------

    async def creer_destination_postgres(
        self,
        workspace_id: str,
        nom: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        schema: str = "public",
    ) -> str:
        corps = await self._appeler(
            "POST",
            "/api/public/v1/destinations",
            json={
                "name": nom,
                "workspaceId": workspace_id,
                "configuration": {
                    "destinationType": "postgres",
                    "host": host,
                    "port": port,
                    "database": database,
                    "username": username,
                    "password": password,
                    "schema": schema,
                    "ssl_mode": {"mode": "disable"},
                    "tunnel_method": {"tunnel_method": "NO_TUNNEL"},
                },
            },
        )
        return corps["destinationId"]

    # --- Connexions et synchronisation ----------------------------------------

    async def creer_connexion(
        self, source_id: str, destination_id: str, nom: str, prefixe: str = ""
    ) -> str:
        """Cree la connexion sans flux selectionne : `selectionner_streams` les
        active ensuite. Deux appels separes parce que c'est la sequence
        reellement validee contre l'API (une tentative d'envoyer les flux des
        la creation n'a pas ete confirmee).

        `prefixe` est ajoute par Airbyte devant chaque table ecrite dans
        l'entrepot : c'est ce qui evite que deux sources se marchent dessus.
        """
        corps = await self._appeler(
            "POST",
            "/api/public/v1/connections",
            json={
                "sourceId": source_id,
                "destinationId": destination_id,
                "name": nom,
                "prefix": prefixe,
            },
        )
        return corps["connectionId"]

    async def selectionner_streams(self, connection_id: str, noms_flux: list[str]) -> None:
        await self._appeler(
            "PATCH",
            f"/api/public/v1/connections/{connection_id}",
            json={
                "configurations": {
                    "streams": [
                        {"name": nom, "syncMode": "full_refresh_overwrite"} for nom in noms_flux
                    ]
                }
            },
        )

    async def declencher_sync(self, connection_id: str) -> int:
        corps = await self._appeler(
            "POST",
            "/api/public/v1/jobs",
            json={"connectionId": connection_id, "jobType": "sync"},
        )
        return corps["jobId"]

    async def obtenir_job(self, job_id: int) -> dict:
        return await self._appeler("GET", f"/api/public/v1/jobs/{job_id}")

    async def job_en_cours(self, connection_id: str) -> int | None:
        """L'id du job de synchronisation non termine sur cette connexion, s'il y en a un.

        Airbyte declenche parfois une synchronisation de lui-meme (a la
        selection des flux, notamment) et refuse alors d'en lancer une seconde.
        Savoir laquelle tourne vaut mieux que de rendre une erreur.
        """
        corps = await self._appeler(
            "GET", "/api/public/v1/jobs", params={"connectionId": connection_id, "limit": 10}
        )
        for job in corps.get("data", []):
            if job.get("status") in ("pending", "running", "incomplete"):
                return job.get("jobId")
        return None

    async def planifier_connexion(self, connection_id: str, cron: str | None) -> None:
        """Une expression cron (format Quartz, six champs) ou None pour repasser en manuel."""
        planification = (
            {"scheduleType": "cron", "cronExpression": cron} if cron else {"scheduleType": "manual"}
        )
        await self._appeler(
            "PATCH",
            f"/api/public/v1/connections/{connection_id}",
            json={"schedule": planification},
        )

    async def supprimer_connexion(self, connection_id: str) -> None:
        await self._appeler("DELETE", f"/api/public/v1/connections/{connection_id}")

    async def supprimer_source(self, source_id: str) -> None:
        await self._appeler("DELETE", f"/api/public/v1/sources/{source_id}")

    # --- Authentification -----------------------------------------------

    async def _appeler(self, methode: str, chemin: str, **kwargs) -> dict:
        jeton = await self._jeton_valide()
        reponse = await self._http.request(
            methode,
            f"{self._base_url}{chemin}",
            headers={"Authorization": f"Bearer {jeton}"},
            **kwargs,
        )
        reponse.raise_for_status()
        # Une suppression repond 204 sans corps.
        return reponse.json() if reponse.content else {}

    async def _jeton_valide(self) -> str:
        maintenant = datetime.now(UTC)
        if self._jeton is None or self._expire_le is None or maintenant >= self._expire_le:
            await self._authentifier()
        assert self._jeton is not None
        return self._jeton

    async def _authentifier(self) -> None:
        reponse = await self._http.post(
            f"{self._base_url}/api/public/v1/applications/token",
            json={"client_id": self._client_id, "client_secret": self._client_secret},
        )
        reponse.raise_for_status()
        corps = reponse.json()
        self._jeton = corps["access_token"]
        duree = timedelta(seconds=corps.get("expires_in", 3600)) - MARGE_EXPIRATION
        self._expire_le = datetime.now(UTC) + duree


@lru_cache
def get_airbyte_client() -> AirbyteClient:
    reglages = get_settings()
    return AirbyteClient(
        reglages.airbyte_base_url, reglages.airbyte_client_id, reglages.airbyte_client_secret
    )
