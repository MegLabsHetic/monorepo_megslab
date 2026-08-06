"""Le client Airbyte s'authentifie, reutilise son jeton, et le renouvelle a expiration.

Aucun appel reseau reel : un transport factice rejoue des reponses preparees.
"""

import httpx

from app.core.airbyte_client import AirbyteClient


def _client_factice(reponses: list[httpx.Response]) -> tuple[AirbyteClient, list[httpx.Request]]:
    appels: list[httpx.Request] = []

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        appels.append(requete)
        return reponses.pop(0)

    http = httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire))
    return AirbyteClient("http://airbyte.local", "id", "secret", http=http), appels


def _appels_authentification(appels: list[httpx.Request]) -> list[httpx.Request]:
    return [r for r in appels if r.url.path.endswith("/applications/token")]


async def test_authentifie_puis_appelle_avec_le_jeton_obtenu() -> None:
    client, appels = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"workspaceId": "abc"}),
        ]
    )

    workspace_id = await client.creer_workspace("Espace de Ada")

    assert workspace_id == "abc"
    assert appels[1].headers["authorization"] == "Bearer jeton-1"


async def test_le_jeton_est_reutilise_tant_qu_il_n_est_pas_expire() -> None:
    client, appels = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"workspaceId": "a"}),
            httpx.Response(200, json={"workspaceId": "b"}),
        ]
    )

    await client.creer_workspace("Un")
    await client.creer_workspace("Deux")

    assert len(_appels_authentification(appels)) == 1


async def test_reauthentifie_une_fois_le_jeton_expire() -> None:
    client, appels = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 0}),
            httpx.Response(200, json={"workspaceId": "a"}),
            httpx.Response(200, json={"access_token": "jeton-2", "expires_in": 3600}),
            httpx.Response(200, json={"workspaceId": "b"}),
        ]
    )

    await client.creer_workspace("Un")
    await client.creer_workspace("Deux")

    assert len(_appels_authentification(appels)) == 2
