"""Client pour l'API publique d'Airbyte : authentification et workspaces.

Ne connait que le protocole HTTP d'Airbyte. La decision de quand creer un
workspace (et quoi faire si Airbyte est injoignable) appartient a l'appelant.
"""

from datetime import UTC, datetime, timedelta
from functools import lru_cache

import httpx

from app.core.config import get_settings

MARGE_EXPIRATION = timedelta(seconds=60)


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
        self._http = http or httpx.AsyncClient()
        self._jeton: str | None = None
        self._expire_le: datetime | None = None

    async def creer_workspace(self, nom: str) -> str:
        """Cree un workspace Airbyte et renvoie son id."""
        corps = await self._appeler("POST", "/api/public/v1/workspaces", json={"name": nom})
        return corps["workspaceId"]

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
        return reponse.json()

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
