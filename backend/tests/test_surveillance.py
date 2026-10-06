"""Une surveillance rejoue du SQL valide et decide de prevenir, sans appeler de modele."""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.duckdb_engine import Resultat
from app.core.errors import ErreurUtilisateur
from app.core.ordonnanceur import Ordonnanceur
from app.models.organization import Organization
from app.models.surveillance import Declencheur
from app.models.user import User
from app.models.workspace import Workspace
from app.services.surveillance_service import SURVEILLANCES_MAX, SurveillanceService


class FauxMoteur:
    """Rend la serie qu'on lui donne, pour toute requete."""

    lignes: list = [(f"2024-{m:02d}", 100.0 + m) for m in range(1, 13)]

    def __init__(self, schema: str) -> None:
        self.schema_entrepot = schema
        self.requetes: list[str] = []

    def executer(self, sql: str, lignes_max: int = 5000) -> Resultat:
        self.requetes.append(sql)
        return Resultat(colonnes=["mois", "valeur"], lignes=self.lignes, tronque=False)


def _moteur_rendant(lignes):
    class Moteur(FauxMoteur):
        pass

    Moteur.lignes = lignes
    return Moteur


async def _monde(db: AsyncSession):
    organisation = Organization(nom="Acme")
    ada = User(email="ada@example.com", nom_complet="Ada")
    db.add_all([organisation, ada])
    await db.flush()
    espace = Workspace(organization_id=organisation.id, nom="General", schema_entrepot="ws_x")
    db.add(espace)
    await db.flush()
    return espace, ada


SQL = 'SELECT mois, valeur FROM entrepot."ventes"'


async def test_creer_valide_le_sql_par_le_garde_fou(db: AsyncSession) -> None:
    espace, ada = await _monde(db)
    service = SurveillanceService(db, FauxMoteur)
    with pytest.raises(ErreurUtilisateur) as leve:
        await service.creer(
            espace,
            ada,
            "Suppression",
            'DELETE FROM entrepot."ventes"',
            Declencheur.TOUJOURS,
            None,
            8,
        )
    assert leve.value.code_http == 422


async def test_un_seuil_sans_valeur_est_refuse(db: AsyncSession) -> None:
    espace, ada = await _monde(db)
    service = SurveillanceService(db, FauxMoteur)
    with pytest.raises(ErreurUtilisateur):
        await service.creer(espace, ada, "Retours", SQL, Declencheur.SEUIL_DEPASSE, None, 8)


async def test_le_declencheur_de_seuil_previent_quand_il_est_franchi(db: AsyncSession) -> None:
    espace, ada = await _monde(db)
    moteur = _moteur_rendant([("total", 42.0)])
    service = SurveillanceService(db, moteur)
    s = await service.creer(espace, ada, "Retours", SQL, Declencheur.SEUIL_DEPASSE, 10.0, 8)
    verdict = await service.executer(espace, s)
    assert verdict.notifier is True
    assert "42" in verdict.message


async def test_le_declencheur_de_seuil_se_tait_quand_il_ne_l_est_pas(db: AsyncSession) -> None:
    espace, ada = await _monde(db)
    service = SurveillanceService(db, _moteur_rendant([("total", 3.0)]))
    s = await service.creer(espace, ada, "Retours", SQL, Declencheur.SEUIL_DEPASSE, 10.0, 8)
    assert (await service.executer(espace, s)).notifier is False


async def test_une_serie_reguliere_ne_declenche_aucune_anomalie(db: AsyncSession) -> None:
    espace, ada = await _monde(db)
    service = SurveillanceService(db, FauxMoteur)
    s = await service.creer(espace, ada, "Ventes", SQL, Declencheur.ANOMALIE, None, 8)
    assert (await service.executer(espace, s)).notifier is False


async def test_l_execution_consigne_toujours_son_etat(db: AsyncSession) -> None:
    """Meme sans notification, on doit pouvoir dire quand elle a tourne."""
    espace, ada = await _monde(db)
    service = SurveillanceService(db, FauxMoteur)
    s = await service.creer(espace, ada, "Ventes", SQL, Declencheur.ANOMALIE, None, 8)
    await service.executer(espace, s)
    assert s.derniere_execution is not None
    assert s.dernier_etat


async def test_une_requete_en_echec_ne_leve_pas_mais_se_consigne(db: AsyncSession) -> None:
    espace, ada = await _monde(db)

    class MoteurCasse(FauxMoteur):
        def executer(self, sql: str, lignes_max: int = 5000):
            from app.core.duckdb_engine import ErreurRequete

            raise ErreurRequete("table disparue")

    service = SurveillanceService(db, MoteurCasse)
    s = await service.creer(espace, ada, "Ventes", SQL, Declencheur.ANOMALIE, None, 8)
    verdict = await service.executer(espace, s)
    assert verdict.notifier is False
    assert verdict.erreur
    assert "echec" in s.dernier_etat


async def test_un_espace_est_plafonne_en_nombre_de_surveillances(db: AsyncSession) -> None:
    espace, ada = await _monde(db)
    service = SurveillanceService(db, FauxMoteur)
    for i in range(SURVEILLANCES_MAX):
        await service.creer(espace, ada, f"S{i}", SQL, Declencheur.TOUJOURS, None, 8)
    with pytest.raises(ErreurUtilisateur) as leve:
        await service.creer(espace, ada, "De trop", SQL, Declencheur.TOUJOURS, None, 8)
    assert leve.value.code_http == 409


# --- Ordonnanceur ------------------------------------------------------------


class Horloge:
    def __init__(self, heure: int = 8) -> None:
        self.heure = heure

    def __call__(self) -> datetime:
        return datetime(2026, 9, 22, self.heure, tzinfo=UTC)


@pytest.mark.asyncio
async def test_l_ordonnanceur_n_execute_qu_une_fois_par_heure() -> None:
    horloge = Horloge(8)
    tours: list[int] = []

    async def tache(heure: int) -> None:
        tours.append(heure)

    ordonnanceur = Ordonnanceur(tache, horloge)
    assert await ordonnanceur.tour() is True
    assert await ordonnanceur.tour() is False, "deux tours dans la meme heure"
    horloge.heure = 9
    assert await ordonnanceur.tour() is True
    assert tours == [8, 9]


@pytest.mark.asyncio
async def test_une_tache_qui_echoue_n_arrete_pas_l_ordonnanceur() -> None:
    """Une surveillance mal ecrite ne doit pas eteindre toutes les autres."""
    horloge = Horloge(8)
    appels: list[int] = []

    async def tache(heure: int) -> None:
        appels.append(heure)
        raise RuntimeError("requete impossible")

    ordonnanceur = Ordonnanceur(tache, horloge)
    assert await ordonnanceur.tour() is True
    horloge.heure = 9
    assert await ordonnanceur.tour() is True
    assert appels == [8, 9]


@pytest.mark.asyncio
async def test_l_ordonnanceur_s_arrete_proprement() -> None:
    async def tache(heure: int) -> None:
        await asyncio.sleep(0)

    ordonnanceur = Ordonnanceur(tache, Horloge())
    ordonnanceur.demarrer()
    await asyncio.sleep(0)
    await ordonnanceur.arreter()
