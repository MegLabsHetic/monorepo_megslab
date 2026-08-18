"""Le client Airbyte s'authentifie, reutilise son jeton, et le renouvelle a expiration.

Aucun appel reseau reel : un transport factice rejoue des reponses preparees.
"""

import httpx

from app.core.airbyte_client import AirbyteClient, StreamDecouvert


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


async def test_creer_source_transmet_la_configuration_telle_quelle() -> None:
    client, appels = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"sourceId": "source-1"}),
        ]
    )

    source_id = await client.creer_source(
        "workspace-1", "Ma source", {"sourceType": "mysql", "host": "hote"}
    )

    assert source_id == "source-1"
    assert b'"sourceType":"mysql"' in appels[1].content


async def test_lister_streams_extrait_noms_namespace_et_colonnes() -> None:
    client, _ = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(
                200,
                json=[
                    {
                        "streamName": "customers",
                        "streamnamespace": "public",
                        "propertyFields": [["id"], ["email"]],
                    }
                ],
            ),
        ]
    )

    flux = await client.lister_streams("source-1")

    assert flux == [StreamDecouvert(nom="customers", namespace="public", colonnes=["id", "email"])]


async def test_creer_destination_postgres_renvoie_son_id() -> None:
    client, _ = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"destinationId": "destination-1"}),
        ]
    )

    destination_id = await client.creer_destination_postgres(
        "workspace-1", "Mon entrepot", "hote", 5432, "warehouse", "user", "mdp"
    )

    assert destination_id == "destination-1"


async def test_creer_connexion_puis_selectionner_streams() -> None:
    client, appels = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"connectionId": "connexion-1"}),
            httpx.Response(200, json={"connectionId": "connexion-1"}),
        ]
    )

    connection_id = await client.creer_connexion("source-1", "destination-1", "Ma connexion")
    await client.selectionner_streams(connection_id, ["customers", "orders"])

    assert connection_id == "connexion-1"
    assert appels[2].method == "PATCH"


async def test_declencher_sync_renvoie_le_job_id() -> None:
    client, _ = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"jobId": 42, "status": "pending"}),
        ]
    )

    job_id = await client.declencher_sync("connexion-1")

    assert job_id == 42


async def test_obtenir_job_renvoie_le_statut() -> None:
    client, _ = _client_factice(
        [
            httpx.Response(200, json={"access_token": "jeton-1", "expires_in": 3600}),
            httpx.Response(200, json={"jobId": 42, "status": "succeeded", "rowsSynced": 100}),
        ]
    )

    job = await client.obtenir_job(42)

    assert job["status"] == "succeeded"
    assert job["rowsSynced"] == 100
