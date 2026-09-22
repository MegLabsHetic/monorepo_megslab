"""La route de configuration dit ce qui est applique, pas ce qui est ecrit."""

import pytest

from app.api.configuration import _chaine_de, modeles
from app.core import llm_client


class ReglagesFactices:
    anthropic_api_key = "factice"
    ovhcloud_api_key = "factice"
    scaleway_api_key = "factice"
    ionos_api_key = "factice"

    def __init__(self, commune="", analyste="", redacteur="", viz=""):
        self.llm_chaine = commune
        self.llm_chaine_analyste = analyste
        self.llm_chaine_redacteur = redacteur
        self.llm_chaine_viz = viz


@pytest.fixture
def reglages(monkeypatch):
    def poser(**kw):
        r = ReglagesFactices(**kw)
        monkeypatch.setattr(llm_client, "get_settings", lambda: r)
        return r

    return poser


def test_sans_configuration_les_trois_agents_sont_chez_le_fournisseur_historique(reglages):
    reglages()
    for agent in ("analyste", "redacteur", "viz"):
        chaine = _chaine_de(agent)
        assert [f.fournisseur for f in chaine.fournisseurs] == ["anthropic"]
        assert chaine.fournisseurs[0].dans_l_union_europeenne is False


def test_chaque_agent_expose_sa_propre_chaine(reglages):
    reglages(
        commune="ovhcloud:gpt-oss-20b",
        analyste="ovhcloud:Qwen3.5-397B-A17B,scaleway:Qwen3.5-397B-A17B",
    )
    analyste = _chaine_de("analyste")
    assert [f.fournisseur for f in analyste.fournisseurs] == ["ovhcloud", "scaleway"]
    assert _chaine_de("viz").fournisseurs[0].modele == "gpt-oss-20b"


def test_la_localisation_d_ovhcloud_est_marquee_verifiee(reglages):
    """Constatee par resolution DNS et enregistrement RIPE, pas declaree."""
    reglages(commune="ovhcloud:gpt-oss-120b")
    f = _chaine_de("viz").fournisseurs[0]
    assert (f.pays, f.ville, f.localisation_verifiee) == ("France", "Gravelines", True)


async def test_une_chaine_entierement_francaise_est_signalee_comme_europeenne(reglages, db):
    reglages(commune="ovhcloud:gpt-oss-120b,scaleway:gpt-oss-120b")
    rapport = await modeles(_=None, db=db)
    assert rapport.entierement_europeenne is True
    assert rapport.rabattement_actif is True


async def test_le_fournisseur_historique_ne_passe_pas_pour_europeen(reglages, db):
    reglages()
    rapport = await modeles(_=None, db=db)
    assert rapport.entierement_europeenne is False
    assert rapport.rabattement_actif is False


async def test_les_cles_ne_sortent_jamais_en_clair(reglages, db) -> None:
    """L'interface recoit une empreinte, jamais la cle."""
    from app.services.reglages_llm_service import ReglagesLLMService

    reglages()
    await ReglagesLLMService(db).poser_cle("ovhcloud", "sk-secret-a-ne-pas-divulguer")
    rapport = await modeles(_=None, db=db)
    ovh = next(c for c in rapport.cles if c.fournisseur == "ovhcloud")
    assert ovh.definie is True
    assert ovh.origine == "base"
    assert "secret" not in ovh.empreinte
    assert ovh.empreinte == "sk-s...guer"


async def test_vider_une_surcharge_rend_la_main_a_l_environnement(reglages, db) -> None:
    from app.core.llm_client import construire_la_chaine
    from app.services.recharger_reglages import recharger
    from app.services.reglages_llm_service import ReglagesLLMService

    reglages(commune="ovhcloud:gpt-oss-20b")
    service = ReglagesLLMService(db)
    await service.poser_chaine("analyste", "ionos:gpt-oss-120b")
    await recharger(db)
    assert construire_la_chaine("analyste").noms == ["ionos/gpt-oss-120b"]

    await service.poser_chaine("analyste", "")
    await recharger(db)
    assert construire_la_chaine("analyste").noms == ["ovhcloud/gpt-oss-20b"]
