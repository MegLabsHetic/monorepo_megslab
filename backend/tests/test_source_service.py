"""Connecter une source la decouvre ; synchroniser la relie a l'entrepot et lance un sync."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.errors import ErreurUtilisateur
from app.models.data_source import StatutSource
from app.models.organization import Organization
from app.models.workspace import Workspace
from app.services import source_service
from app.services.source_service import SourceService


async def _espace(db: AsyncSession) -> Workspace:
    espace = Organization(nom="Acme")
    db.add(espace)
    await db.flush()
    espace = Workspace(
        organization_id=espace.id,
        nom="General",
        airbyte_workspace_id="workspace-test",
        airbyte_destination_id="destination-test",
        schema_entrepot=f"org_{espace.id}",
    )
    db.add(espace)
    await db.flush()
    return espace


async def test_connecter_postgres_enregistre_la_source_et_renvoie_les_flux(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    espace = await _espace(db)
    service = SourceService(db, airbyte_client_factice)

    source, flux = await service.connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    assert source.airbyte_source_id == "source-test"
    assert source.statut == StatutSource.CONNECTEE
    assert source.schema_entrepot == espace.schema_entrepot
    assert [f.nom for f in flux] == ["customers"]


async def test_synchroniser_cree_la_connexion_une_seule_fois(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    espace = await _espace(db)
    service = SourceService(db, airbyte_client_factice)
    source, _ = await service.connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    job_id = await service.synchroniser(source, espace, ["customers"])

    assert job_id == 1
    assert source.airbyte_connection_id == "connexion-test"
    assert source.statut == StatutSource.SYNCHRONISATION


def _client_airbyte(gestionnaire) -> AirbyteClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire))
    return AirbyteClient("http://airbyte.local", "id", "secret", http=http)


async def test_une_synchronisation_deja_en_cours_est_suivie_au_lieu_d_echouer(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    """Airbyte repond 409 quand il a deja lance une synchronisation lui-meme :
    on doit rendre le job en cours, pas une erreur."""
    espace = await _espace(db)
    source, _ = await SourceService(db, airbyte_client_factice).connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        if "/connections" in chemin:
            return httpx.Response(200, json={"connectionId": "connexion-test"})
        if chemin.endswith("/jobs") and requete.method == "POST":
            return httpx.Response(409, json={"message": "sync already running"})
        if chemin.endswith("/jobs"):
            return httpx.Response(200, json={"data": [{"jobId": 77, "status": "running"}]})
        return httpx.Response(200, json={})

    service = SourceService(db, _client_airbyte(gestionnaire))
    job_id = await service.synchroniser(source, espace, ["customers"])

    assert job_id == 77
    assert source.statut == StatutSource.SYNCHRONISATION


async def test_un_409_transitoire_est_reessaye(
    db: AsyncSession, airbyte_client_factice: AirbyteClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Airbyte verrouille brievement la connexion apres la selection des flux :
    il repond alors 409 avec une liste de jobs vide. Constate en reel."""
    monkeypatch.setattr(source_service, "DELAI_ENTRE_TENTATIVES_SECONDES", 0)
    espace = await _espace(db)
    source, _ = await SourceService(db, airbyte_client_factice).connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    tentatives = {"n": 0}

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        if "/connections" in chemin:
            return httpx.Response(200, json={"connectionId": "connexion-test"})
        if chemin.endswith("/jobs") and requete.method == "POST":
            tentatives["n"] += 1
            if tentatives["n"] == 1:
                return httpx.Response(409, json={"message": "verrou"})
            return httpx.Response(200, json={"jobId": 12, "status": "pending"})
        if chemin.endswith("/jobs"):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={})

    service = SourceService(db, _client_airbyte(gestionnaire))
    job_id = await service.synchroniser(source, espace, ["customers"])

    assert job_id == 12
    assert tentatives["n"] == 2


async def test_la_connexion_est_enregistree_meme_si_le_declenchement_echoue(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    """Sinon chaque nouvelle tentative creerait une connexion Airbyte orpheline."""
    espace = await _espace(db)
    source, _ = await SourceService(db, airbyte_client_factice).connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        if "/connections" in chemin:
            return httpx.Response(200, json={"connectionId": "connexion-creee"})
        return httpx.Response(500, json={"message": "boum"})

    service = SourceService(db, _client_airbyte(gestionnaire))
    with pytest.raises(ErreurUtilisateur):
        await service.synchroniser(source, espace, ["customers"])

    assert source.airbyte_connection_id == "connexion-creee"


async def test_statut_sync_marque_la_source_prete_quand_le_job_reussit(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    espace = await _espace(db)
    service = SourceService(db, airbyte_client_factice)
    source, _ = await service.connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )
    await service.synchroniser(source, espace, ["customers"])

    job = await service.statut_sync(source, 1)

    assert job["status"] == "succeeded"
    assert source.statut == StatutSource.PRETE


async def test_seules_les_sources_inconnues_sont_proposees_a_l_import(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    """Une source deja referencee par MegLabs ne doit pas etre proposee deux fois."""
    espace = await _espace(db)
    service = SourceService(db, airbyte_client_factice)
    await service.connecter_base(
        espace, "postgres", "Deja connue", "hote", 5432, "base", "user", "mdp"
    )

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        if requete.url.path.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        return httpx.Response(
            200,
            json={
                "data": [
                    {"sourceId": "source-test", "name": "Deja connue", "sourceType": "postgres"},
                    {"sourceId": "orpheline", "name": "Creee dans Airbyte", "sourceType": "stripe"},
                ]
            },
        )

    importables = await SourceService(
        db, _client_airbyte(gestionnaire)
    ).sources_airbyte_importables(espace)

    assert [s.id for s in importables] == ["orpheline"]


async def test_importer_une_source_airbyte_la_reference_avec_son_schema(
    db: AsyncSession,
) -> None:
    """Adopter une source ne demande aucun identifiant : ils restent chez Airbyte."""
    espace = await _espace(db)

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        if chemin.endswith("/streams"):
            return httpx.Response(
                200,
                json=[
                    {
                        "streamName": "charges",
                        "streamnamespace": "stripe",
                        "propertyFields": [["id"], ["amount"]],
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {"sourceId": "orpheline", "name": "Stripe production", "sourceType": "stripe"}
                ]
            },
        )

    source = await SourceService(db, _client_airbyte(gestionnaire)).importer_depuis_airbyte(
        espace, "orpheline"
    )

    assert source.nom == "Stripe production"
    assert source.type_source == "stripe"
    assert source.airbyte_source_id == "orpheline"
    assert [flux["nom"] for flux in source.flux_decouverts] == ["charges"]


async def test_planifier_pose_un_cron_quartz_cote_airbyte(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    espace = await _espace(db)
    source, _ = await SourceService(db, airbyte_client_factice).connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )
    corps_recus: list[dict] = []

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        if "/connections" in chemin and requete.method == "PATCH":
            corps_recus.append(__import__("json").loads(requete.content))
            return httpx.Response(200, json={})
        if "/connections" in chemin:
            return httpx.Response(200, json={"connectionId": "connexion-test"})
        return httpx.Response(200, json={})

    service = SourceService(db, _client_airbyte(gestionnaire))
    source = await service.planifier(source, espace, "quotidienne")

    assert source.planification == "quotidienne"
    assert corps_recus[-1] == {
        "schedule": {"scheduleType": "cron", "cronExpression": "0 0 6 * * ?"}
    }

    await service.planifier(source, espace, "manuelle")
    assert corps_recus[-1] == {"schedule": {"scheduleType": "manual"}}

    with pytest.raises(ErreurUtilisateur):
        await service.planifier(source, espace, "toutes-les-minutes")


async def test_supprimer_retire_airbyte_puis_les_tables_puis_la_source(
    db: AsyncSession, airbyte_client_factice: AirbyteClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    espace = await _espace(db)
    service = SourceService(db, airbyte_client_factice)
    source, _ = await service.connecter_base(
        espace, "postgres", "Ma base", "hote", 5432, "base", "user", "mdp"
    )
    await service.synchroniser(source, espace, ["customers"])
    prefixe = source.prefixe_entrepot
    supprimees: list[tuple[str, list[str]]] = []

    def faux_supprimer(self, tables):  # noqa: ANN001
        supprimees.append((self._schema, tables))

    monkeypatch.setattr(source_service.EntrepotWriter, "supprimer_tables", faux_supprimer)
    appels: list[tuple[str, str]] = []

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        appels.append((requete.method, chemin))
        return httpx.Response(204)

    await SourceService(db, _client_airbyte(gestionnaire)).supprimer(source)

    assert appels == [
        ("DELETE", "/api/public/v1/connections/connexion-test"),
        ("DELETE", "/api/public/v1/sources/source-test"),
    ]
    assert supprimees == [(espace.schema_entrepot, [f"{prefixe}customers"])]
    assert await service.lister(espace) == []


async def test_importer_une_source_deja_connue_est_refuse(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    espace = await _espace(db)

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        if requete.url.path.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "j", "expires_in": 3600})
        return httpx.Response(200, json={"data": []})

    with pytest.raises(ErreurUtilisateur):
        await SourceService(db, _client_airbyte(gestionnaire)).importer_depuis_airbyte(
            espace, "inexistante"
        )
