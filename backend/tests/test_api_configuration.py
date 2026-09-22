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


@pytest.mark.asyncio
async def test_une_chaine_entierement_francaise_est_signalee_comme_europeenne(reglages):
    reglages(commune="ovhcloud:gpt-oss-120b,scaleway:gpt-oss-120b")
    rapport = await modeles(_=None)
    assert rapport.entierement_europeenne is True
    assert rapport.rabattement_actif is True


@pytest.mark.asyncio
async def test_le_fournisseur_historique_ne_passe_pas_pour_europeen(reglages):
    reglages()
    rapport = await modeles(_=None)
    assert rapport.entierement_europeenne is False
    assert rapport.rabattement_actif is False
