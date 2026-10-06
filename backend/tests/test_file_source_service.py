"""Un fichier depose devient une source, et les depots invalides sont refusees."""

import io

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.organization import Organization
from app.models.workspace import Workspace
from app.services import file_source_service
from app.services.file_source_service import FileSourceService


def _depot(nom: str, contenu: bytes) -> UploadFile:
    return UploadFile(filename=nom, file=io.BytesIO(contenu))


async def _espace(db: AsyncSession) -> Workspace:
    espace = Organization(nom="Acme")
    db.add(espace)
    await db.flush()
    espace = Workspace(
        organization_id=espace.id,
        nom="General",
        airbyte_workspace_id="w",
        airbyte_destination_id="d",
        schema_entrepot=f"org_{espace.id}",
    )
    db.add(espace)
    await db.flush()
    return espace


async def test_un_format_non_supporte_est_refuse(db: AsyncSession) -> None:
    espace = await _espace(db)

    with pytest.raises(ErreurUtilisateur) as capture:
        await FileSourceService(db).importer_fichier(espace, _depot("note.txt", b"bonjour"))

    assert capture.value.code_http == 415


async def test_un_fichier_vide_est_refuse(db: AsyncSession) -> None:
    espace = await _espace(db)

    with pytest.raises(ErreurUtilisateur) as capture:
        await FileSourceService(db).importer_fichier(espace, _depot("vide.csv", b""))

    assert capture.value.code_http == 422


async def test_un_fichier_trop_gros_est_interrompu_avant_la_fin(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La limite doit s'appliquer pendant l'ecriture, pas apres avoir tout accepte."""
    espace = await _espace(db)
    monkeypatch.setattr(file_source_service, "TAILLE_MAX_OCTETS", 10)
    monkeypatch.setattr(file_source_service, "TAILLE_MORCEAU", 4)

    with pytest.raises(ErreurUtilisateur) as capture:
        await FileSourceService(db).importer_fichier(espace, _depot("gros.csv", b"a" * 5_000))

    assert capture.value.code_http == 413
