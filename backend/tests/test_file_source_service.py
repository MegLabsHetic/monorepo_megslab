"""Un fichier depose devient une source, et les depots invalides sont refusees."""

import io

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.organization import Organization
from app.services import file_source_service
from app.services.file_source_service import FileSourceService


def _depot(nom: str, contenu: bytes) -> UploadFile:
    return UploadFile(filename=nom, file=io.BytesIO(contenu))


async def _organisation(db: AsyncSession) -> Organization:
    organisation = Organization(nom="Acme", airbyte_workspace_id="w", airbyte_destination_id="d")
    db.add(organisation)
    await db.flush()
    return organisation


async def test_un_format_non_supporte_est_refuse(db: AsyncSession) -> None:
    organisation = await _organisation(db)

    with pytest.raises(ErreurUtilisateur) as capture:
        await FileSourceService(db).importer_fichier(organisation, _depot("note.txt", b"bonjour"))

    assert capture.value.code_http == 415


async def test_un_fichier_vide_est_refuse(db: AsyncSession) -> None:
    organisation = await _organisation(db)

    with pytest.raises(ErreurUtilisateur) as capture:
        await FileSourceService(db).importer_fichier(organisation, _depot("vide.csv", b""))

    assert capture.value.code_http == 422


async def test_un_fichier_trop_gros_est_interrompu_avant_la_fin(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La limite doit s'appliquer pendant l'ecriture, pas apres avoir tout accepte."""
    organisation = await _organisation(db)
    monkeypatch.setattr(file_source_service, "TAILLE_MAX_OCTETS", 10)
    monkeypatch.setattr(file_source_service, "TAILLE_MORCEAU", 4)

    with pytest.raises(ErreurUtilisateur) as capture:
        await FileSourceService(db).importer_fichier(organisation, _depot("gros.csv", b"a" * 5_000))

    assert capture.value.code_http == 413
