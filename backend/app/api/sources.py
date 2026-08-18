"""Routes de connexion et de synchronisation des sources de donnees."""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import organisation_courante
from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.config import get_settings
from app.core.connecteurs import CONNECTEURS
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource
from app.models.organization import Organization
from app.schemas.source import (
    ApercuReponse,
    ConnexionBaseDemande,
    FluxReponse,
    ProfilColonneReponse,
    SourceImportableReponse,
    SourceReponse,
    StatutSyncReponse,
    SynchronisationDemande,
    SynchronisationReponse,
    TableReponse,
    TypeConnecteurReponse,
)
from app.services.file_source_service import FileSourceService
from app.services.source_service import SourceService
from app.services.warehouse_service import WarehouseService

router = APIRouter(prefix="/sources", tags=["sources"])


def _en_reponse(source: DataSource) -> SourceReponse:
    return SourceReponse(
        id=source.id,
        nom=source.nom,
        type_source=source.type_source,
        statut=source.statut.value,
        schema_entrepot=source.schema_entrepot,
        nb_tables=source.nb_tables,
        nb_colonnes=source.nb_colonnes,
        flux_disponibles=[
            FluxReponse(
                nom=flux["nom"], namespace=flux["namespace"], colonnes=flux.get("colonnes", [])
            )
            for flux in source.flux_decouverts or []
        ],
        flux_selectionnes=source.flux_selectionnes or [],
        cree_le=source.cree_le,
        lien_airbyte=_lien_airbyte(source),
    )


def _lien_airbyte(source: DataSource) -> str | None:
    """Le lien vers la source dans Airbyte, pour la configuration avancee.

    Reserve aux sources qui en ont une : un fichier depose n'existe pas
    cote Airbyte. Nul aussi tant que l'URL publique n'est pas renseignee,
    plutot que de fabriquer un lien qui ne menerait nulle part.
    """
    base = get_settings().airbyte_url_publique.rstrip("/")
    if not base or source.airbyte_source_id is None:
        return None
    espace = source.organization.airbyte_workspace_id
    return f"{base}/workspaces/{espace}/source/{source.airbyte_source_id}"


@router.get("/connecteurs", response_model=list[TypeConnecteurReponse])
async def lister_connecteurs():
    """Les types de bases que l'interface peut proposer."""
    return [
        TypeConnecteurReponse(cle=c.cle, libelle=c.libelle, port_defaut=c.port_defaut)
        for c in CONNECTEURS.values()
    ]


@router.get("/airbyte", response_model=list[SourceImportableReponse])
async def lister_importables(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Les sources de l'espace Airbyte que MegLabs ne reference pas encore."""
    service = SourceService(db, airbyte_client)
    sources = await service.sources_airbyte_importables(organisation)
    return [SourceImportableReponse(id=s.id, nom=s.nom, type_source=s.type_source) for s in sources]


@router.post("/airbyte/{airbyte_source_id}/importer", response_model=SourceReponse, status_code=201)
async def importer_depuis_airbyte(
    airbyte_source_id: str,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    service = SourceService(db, airbyte_client)
    source = await service.importer_depuis_airbyte(organisation, airbyte_source_id)
    return _en_reponse(source)


@router.get("", response_model=list[SourceReponse])
async def lister(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    sources = await SourceService(db, airbyte_client).lister(organisation)
    return [_en_reponse(source) for source in sources]


@router.post("", response_model=SourceReponse, status_code=201)
async def connecter(
    demande: ConnexionBaseDemande,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    service = SourceService(db, airbyte_client)
    source, _ = await service.connecter_base(
        organisation,
        demande.type_source,
        demande.nom,
        demande.host,
        demande.port,
        demande.database,
        demande.username,
        demande.mot_de_passe,
    )
    return _en_reponse(source)


@router.get("/{source_id}", response_model=SourceReponse)
async def detail(
    source_id: str,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    return _en_reponse(await _charger_source(db, source_id, organisation))


@router.post("/{source_id}/synchroniser", response_model=SynchronisationReponse)
async def synchroniser(
    source_id: str,
    demande: SynchronisationDemande,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await _charger_source(db, source_id, organisation)
    service = SourceService(db, airbyte_client)
    job_id = await service.synchroniser(source, organisation, demande.flux)
    return SynchronisationReponse(job_id=job_id)


@router.get("/{source_id}/synchronisation/{job_id}", response_model=StatutSyncReponse)
async def statut_synchronisation(
    source_id: str,
    job_id: int,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await _charger_source(db, source_id, organisation)
    service = SourceService(db, airbyte_client)
    job = await service.statut_sync(source, job_id)
    return StatutSyncReponse(
        statut=job.get("status", "inconnu"), lignes_synchronisees=job.get("rowsSynced")
    )


@router.post("/fichier", response_model=SourceReponse, status_code=201)
async def importer_fichier(
    fichier: UploadFile = File(...),
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    """Depose un CSV ou un XLSX directement dans l'entrepot, sans passer par Airbyte."""
    source = await FileSourceService(db).importer_fichier(organisation, fichier)
    return _en_reponse(source)


@router.get("/{source_id}/tables", response_model=list[TableReponse])
async def lister_tables(
    source_id: str,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    source = await _charger_source(db, source_id, organisation)
    tables = await WarehouseService(source).lister_tables()
    return [TableReponse(nom=nom, nb_lignes=lignes) for nom, lignes in tables]


@router.get("/{source_id}/tables/{table}/apercu", response_model=ApercuReponse)
async def apercu_table(
    source_id: str,
    table: str,
    limite: int = 50,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    source = await _charger_source(db, source_id, organisation)
    resultat = await WarehouseService(source).apercu(table, min(limite, 200))
    return ApercuReponse(
        colonnes=resultat.colonnes,
        lignes=[[_affichable(valeur) for valeur in ligne] for ligne in resultat.lignes],
        tronque=resultat.tronque,
    )


@router.get("/{source_id}/tables/{table}/profil", response_model=list[ProfilColonneReponse])
async def profil_table(
    source_id: str,
    table: str,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    source = await _charger_source(db, source_id, organisation)
    profils = await WarehouseService(source).profiler(table)
    return [
        ProfilColonneReponse(
            colonne=profil["column_name"],
            type=profil["column_type"],
            nb_valeurs=_entier(profil.get("count")),
            pourcentage_nuls=_reel(profil.get("null_percentage")),
            valeurs_distinctes_approx=_entier(profil.get("approx_unique")),
            minimum=_texte(profil.get("min")),
            maximum=_texte(profil.get("max")),
            moyenne=_texte(profil.get("avg")),
        )
        for profil in profils
    ]


def _affichable(valeur: object) -> object:
    """JSON ne connait ni Decimal, ni date, ni UUID : on les rend en texte.

    Les types simples passent tels quels pour que le frontend puisse encore
    aligner des nombres a droite et compter des booleens.
    """
    if valeur is None or isinstance(valeur, (bool, int, float, str)):
        return valeur
    return str(valeur)


def _entier(valeur: object) -> int | None:
    return None if valeur is None else int(valeur)


def _reel(valeur: object) -> float | None:
    return None if valeur is None else float(valeur)


def _texte(valeur: object) -> str | None:
    return None if valeur is None else str(valeur)


async def _charger_source(
    db: AsyncSession, source_id: str, organisation: Organization
) -> DataSource:
    source = await db.get(DataSource, source_id)
    if source is None or source.organization_id != organisation.id:
        raise ErreurUtilisateur("Source introuvable.", code_http=404)
    return source
