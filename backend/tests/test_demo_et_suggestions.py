"""Le jeu de demonstration se copie en une source ; les suggestions viennent du schema reel."""

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.data import ContexteDonnees
from app.core.config import get_settings
from app.core.duckdb_engine import ColonneProfil, TableProfil
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import Consommation, Reponse
from app.models.organization import Organization
from app.models.workspace import Workspace
from app.services.demo_service import DemoService
from app.services.suggestion_service import Suggestions, SuggestionService


class FauxMoteurDemo:
    def __init__(self, schema: str) -> None:
        self.schema_entrepot = schema

    def lister_tables(self) -> list[str]:
        return ["orders", "customers"]


class FauxWriter:
    copies: list[tuple[str, str, list[str], str]] = []

    def __init__(self, schema: str) -> None:
        self.schema = schema

    def copier_tables(self, schema_source: str, tables: list[str], prefixe: str) -> dict:
        FauxWriter.copies.append((self.schema, schema_source, tables, prefixe))
        return {table: ["id", "valeur"] for table in tables}


async def _espace(db: AsyncSession) -> Workspace:
    organisation = Organization(nom="Acme")
    db.add(organisation)
    await db.flush()
    espace = Workspace(organization_id=organisation.id, nom="General", schema_entrepot="ws_x")
    db.add(espace)
    await db.flush()
    return espace


async def test_charger_la_demo_copie_les_tables_et_enregistre_une_source(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "demo_schema", "demo_olist")
    FauxWriter.copies = []
    espace = await _espace(db)
    service = DemoService(db, FauxMoteurDemo, FauxWriter)  # type: ignore[arg-type]

    source = await service.charger(espace)

    assert FauxWriter.copies == [("ws_x", "demo_olist", ["orders", "customers"], "demo_")]
    assert source.type_source == "demo" and source.statut.value == "prete"
    assert source.flux_selectionnes == ["orders", "customers"]
    assert source.table_entrepot("orders") == "demo_orders"
    assert [f["colonnes"] for f in source.flux_decouverts] == [["id", "valeur"]] * 2

    with pytest.raises(ErreurUtilisateur) as capture:
        await service.charger(espace)  # deja chargee
    assert capture.value.code_http == 409


async def test_sans_schema_configure_la_demo_est_refusee(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "demo_schema", "")
    espace = await _espace(db)
    assert not DemoService.disponible()
    with pytest.raises(ErreurUtilisateur) as capture:
        await DemoService(db, FauxMoteurDemo, FauxWriter).charger(espace)  # type: ignore[arg-type]
    assert capture.value.code_http == 503


class FauxLLM:
    def __init__(self) -> None:
        self.appels = 0

    async def repondre(self, *, instructions, question, format_sortie: type[BaseModel], effort):
        self.appels += 1
        assert format_sortie is Suggestions and effort == "low"
        assert 'entrepot."orders"' in question
        return Reponse(
            contenu=Suggestions(
                questions=["Combien de commandes ?", " Par statut ? ", "", "Q4", "Q5"]
            ),
            consommation=Consommation(100, 20, 0, 0),
        )


async def test_les_suggestions_sont_bornees_puis_servies_depuis_le_cache() -> None:
    contexte = ContexteDonnees(
        tables=(TableProfil("orders", 3, (ColonneProfil("id", "BIGINT", 0.0, 3, None),)),)
    )
    llm = FauxLLM()
    service = SuggestionService(llm)  # type: ignore[arg-type]

    premieres, consommation = await service.proposer("ws_x", contexte)
    assert premieres == ["Combien de commandes ?", "Par statut ?", "Q4"]
    assert consommation is not None and consommation.jetons_total == 120

    secondes, consommation = await service.proposer("ws_x", contexte)
    assert secondes == premieres and consommation is None and llm.appels == 1

    SuggestionService.oublier("ws_x")
    await service.proposer("ws_x", contexte)
    assert llm.appels == 2
