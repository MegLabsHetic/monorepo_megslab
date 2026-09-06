"""Routes de connexion et de synchronisation des sources d'un espace.

Lire (catalogue, apercu, profil) est ouvert a tout membre de l'espace ;
connecter, synchroniser et importer demandent au moins le role MEMBER.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit import journaliser
from app.api.deps import (
    AccesEspace,
    acces_admin_espace,
    acces_analyste,
    acces_courant,
    utilisateur_courant,
)
from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.config import get_settings
from app.core.connecteurs import CONNECTEURS
from app.core.database import get_db
from app.core.duckdb_engine import TableProfil
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.source import (
    ApercuReponse,
    ColonneSanteReponse,
    ConnexionBaseDemande,
    FluxReponse,
    PlanificationDemande,
    ProfilColonneReponse,
    SanteReponse,
    SourceImportableReponse,
    SourceReponse,
    StatutSyncReponse,
    SynchronisationDemande,
    SynchronisationReponse,
    TableReponse,
    TableSanteReponse,
    TypeConnecteurReponse,
)
from app.services.demo_service import DemoService
from app.services.file_source_service import FileSourceService
from app.services.source_service import SourceService
from app.services.warehouse_service import WarehouseService

router = APIRouter(prefix="/espaces/{espace_id}/sources", tags=["sources"])
router_connecteurs = APIRouter(prefix="/connecteurs", tags=["sources"])


def _en_reponse(source: DataSource, espace: Workspace) -> SourceReponse:
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
        planification=source.planification,
        lignes_synchronisees=source.lignes_synchronisees,
        derniere_sync_le=source.derniere_sync_le,
        lien_airbyte=_lien_airbyte(source, espace),
    )


def _lien_airbyte(source: DataSource, espace: Workspace) -> str | None:
    """Le lien vers la source dans Airbyte, pour la configuration avancee.

    Reserve aux sources qui en ont une : un fichier depose n'existe pas
    cote Airbyte. Nul aussi tant que l'URL publique n'est pas renseignee,
    plutot que de fabriquer un lien qui ne menerait nulle part.
    """
    base = get_settings().airbyte_url_publique.rstrip("/")
    if not base or source.airbyte_source_id is None or not espace.airbyte_workspace_id:
        return None
    return f"{base}/workspaces/{espace.airbyte_workspace_id}/source/{source.airbyte_source_id}"


@router_connecteurs.get("", response_model=list[TypeConnecteurReponse])
async def lister_connecteurs():
    """Les types de bases que l'interface peut proposer. Independant de l'espace."""
    return [
        TypeConnecteurReponse(cle=c.cle, libelle=c.libelle, port_defaut=c.port_defaut)
        for c in CONNECTEURS.values()
    ]


@router.get("/airbyte", response_model=list[SourceImportableReponse])
async def lister_importables(
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Les sources de l'espace Airbyte que MegsLab ne reference pas encore."""
    sources = await SourceService(db, airbyte_client).sources_airbyte_importables(acces.espace)
    return [SourceImportableReponse(id=s.id, nom=s.nom, type_source=s.type_source) for s in sources]


@router.post("/airbyte/{airbyte_source_id}/importer", response_model=SourceReponse, status_code=201)
async def importer_depuis_airbyte(
    airbyte_source_id: str,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await SourceService(db, airbyte_client).importer_depuis_airbyte(
        acces.espace, airbyte_source_id
    )
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.adoptee",
        "source",
        source.id,
        source.nom,
        {"type": source.type_source},
        acces.espace.id,
    )
    return _en_reponse(source, acces.espace)


@router.get("", response_model=list[SourceReponse])
async def lister(
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    sources = await SourceService(db, airbyte_client).lister(acces.espace)
    return [_en_reponse(source, acces.espace) for source in sources]


@router.post("", response_model=SourceReponse, status_code=201)
async def connecter(
    demande: ConnexionBaseDemande,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source, _ = await SourceService(db, airbyte_client).connecter_base(
        acces.espace,
        demande.type_source,
        demande.nom,
        demande.host,
        demande.port,
        demande.database,
        demande.username,
        demande.mot_de_passe,
    )
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.connectee",
        "source",
        source.id,
        source.nom,
        {"type": source.type_source},
        acces.espace.id,
    )
    return _en_reponse(source, acces.espace)


@router.post("/fichier", response_model=SourceReponse, status_code=201)
async def importer_fichier(
    fichier: UploadFile = File(...),
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    """Depose un CSV ou un XLSX directement dans l'entrepot, sans passer par Airbyte."""
    source = await FileSourceService(db).importer_fichier(acces.espace, fichier)
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.fichier_importe",
        "source",
        source.id,
        source.nom,
        {},
        acces.espace.id,
    )
    return _en_reponse(source, acces.espace)


@router.get("/demo/disponible")
async def demo_disponible():
    """Vrai si un jeu de demonstration est configure sur ce serveur."""
    return {"disponible": DemoService.disponible()}


@router.post("/demo", response_model=SourceReponse, status_code=201)
async def charger_demo(
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    """Copie le jeu de demonstration dans l'entrepot de l'espace, comme une source ordinaire."""
    source = await DemoService(db).charger(acces.espace)
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.demo_chargee",
        "source",
        source.id,
        source.nom,
        {"tables": len(source.flux_selectionnes or [])},
        acces.espace.id,
    )
    return _en_reponse(source, acces.espace)


@router.get("/{source_id}", response_model=SourceReponse)
async def detail(
    source_id: str,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    return _en_reponse(await _charger_source(db, source_id, acces.espace), acces.espace)


@router.post("/{source_id}/synchroniser", response_model=SynchronisationReponse)
async def synchroniser(
    source_id: str,
    demande: SynchronisationDemande,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await _charger_source(db, source_id, acces.espace)
    job_id = await SourceService(db, airbyte_client).synchroniser(
        source, acces.espace, demande.flux
    )
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.synchronisee",
        "source",
        source.id,
        source.nom,
        {"flux": demande.flux, "job_id": job_id},
        acces.espace.id,
    )
    return SynchronisationReponse(job_id=job_id)


@router.get("/{source_id}/synchronisation/{job_id}", response_model=StatutSyncReponse)
async def statut_synchronisation(
    source_id: str,
    job_id: int,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await _charger_source(db, source_id, acces.espace)
    job = await SourceService(db, airbyte_client).statut_sync(source, job_id)
    return StatutSyncReponse(
        statut=job.get("status", "inconnu"), lignes_synchronisees=job.get("rowsSynced")
    )


@router.get("/{source_id}/tables", response_model=list[TableReponse])
async def lister_tables(
    source_id: str,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    source = await _charger_source(db, source_id, acces.espace)
    tables = await WarehouseService(source).lister_tables()
    return [TableReponse(nom=nom, nb_lignes=lignes) for nom, lignes in tables]


@router.get("/{source_id}/tables/{table}/apercu", response_model=ApercuReponse)
async def apercu_table(
    source_id: str,
    table: str,
    limite: int = 50,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    source = await _charger_source(db, source_id, acces.espace)
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
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    source = await _charger_source(db, source_id, acces.espace)
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


@router.put("/{source_id}/planification", response_model=SourceReponse)
async def planifier(
    source_id: str,
    demande: PlanificationDemande,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Confie a Airbyte le declenchement regulier des synchronisations."""
    source = await _charger_source(db, source_id, acces.espace)
    source = await SourceService(db, airbyte_client).planifier(
        source, acces.espace, demande.frequence
    )
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.planifiee",
        "source",
        source.id,
        source.nom,
        {"frequence": demande.frequence},
        acces.espace.id,
    )
    return _en_reponse(source, acces.espace)


@router.delete("/{source_id}", status_code=204)
async def supprimer(
    source_id: str,
    acces: AccesEspace = Depends(acces_admin_espace),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Retire la source d'Airbyte, fait tomber ses tables dans l'entrepot, l'oublie."""
    source = await _charger_source(db, source_id, acces.espace)
    await SourceService(db, airbyte_client).supprimer(source)
    await journaliser(
        db,
        acces.organisation.id,
        utilisateur,
        "source.supprimee",
        "source",
        source.id,
        source.nom,
        {"tables": len(source.flux_selectionnes or [])},
        acces.espace.id,
    )


@router.get("/{source_id}/sante", response_model=SanteReponse)
async def sante(
    source_id: str,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    """Le profil des tables de la source dans l'entrepot, et ce qui merite un regard."""
    source = await _charger_source(db, source_id, acces.espace)
    profils = await WarehouseService(source).sante()
    tables = [
        TableSanteReponse(
            nom=flux,
            nb_lignes=profil.nb_lignes,
            colonnes=[
                ColonneSanteReponse(
                    nom=c.nom,
                    type=c.type,
                    pourcentage_nuls=round(c.pourcentage_nuls, 1),
                    distinctes_echantillon=c.distinctes_echantillon,
                    modalites=list(c.modalites) if c.modalites else None,
                )
                for c in profil.colonnes
            ],
            alertes=_alertes_table(profil),
        )
        for flux, profil in profils
    ]
    return SanteReponse(
        derniere_sync_le=source.derniere_sync_le,
        lignes_synchronisees=source.lignes_synchronisees,
        alertes=_alertes_source(source, len(tables)),
        tables=tables,
    )


def _alertes_table(profil: TableProfil) -> list[str]:
    alertes = []
    if profil.nb_lignes == 0:
        alertes.append("Table vide.")
    for c in profil.colonnes:
        if c.pourcentage_nuls >= 100:
            alertes.append(f"Colonne « {c.nom} » entierement vide.")
        elif c.pourcentage_nuls >= 50:
            alertes.append(f"Colonne « {c.nom} » vide a {c.pourcentage_nuls:.0f} %.")
        if profil.nb_lignes > 1 and c.type == "VARCHAR" and c.distinctes_echantillon == 1:
            alertes.append(f"Colonne « {c.nom} » constante : une seule valeur.")
    return alertes


def _alertes_source(source: DataSource, nb_tables: int) -> list[str]:
    alertes = []
    if source.derniere_sync_le is None and source.airbyte_source_id is not None:
        alertes.append("Aucune synchronisation reussie enregistree.")
    elif source.derniere_sync_le is not None:
        age = datetime.now(UTC) - _aware(source.derniere_sync_le)
        if age.days >= 7:
            alertes.append(f"Derniere synchronisation il y a {age.days} jours.")
    if source.flux_selectionnes and nb_tables < len(source.flux_selectionnes):
        alertes.append("Certaines tables selectionnees sont absentes de l'entrepot.")
    return alertes


def _aware(instant: datetime) -> datetime:
    return instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)


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


async def _charger_source(db: AsyncSession, source_id: str, espace: Workspace) -> DataSource:
    source = await db.get(DataSource, source_id)
    if source is None or source.workspace_id != espace.id:
        raise ErreurUtilisateur("Source introuvable.", code_http=404)
    return source
