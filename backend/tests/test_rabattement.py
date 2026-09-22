"""Le rabattement ne doit se declencher que sur une panne, jamais sur un resultat."""

import httpx
import pytest
from pydantic import BaseModel

from app.core.consommation import Consommation, Reponse
from app.core.errors import ErreurUtilisateur, FournisseurIndisponible
from app.core.fournisseur_openai import FournisseurOpenAICompatible
from app.core.rabattement import Rabattement
from app.core.tarifs import OVH_GPT_OSS_120B, TarifInconnu, tarif_de


class Plan(BaseModel):
    sql: str
    explication: str = ""


class FournisseurFactice:
    """Repond, ou echoue de la facon demandee, en comptant ses appels."""

    def __init__(self, nom: str, erreur: Exception | None = None) -> None:
        self.nom = nom
        self._erreur = erreur
        self.appels = 0

    async def repondre(self, *, instructions, question, format_sortie, effort="medium"):
        self.appels += 1
        if self._erreur is not None:
            raise self._erreur
        return Reponse(
            contenu=format_sortie(sql=f"SELECT 1 -- {self.nom}"),
            consommation=Consommation(10, 5, 0, 0, tarif=OVH_GPT_OSS_120B),
        )


async def _demander(chaine: Rabattement):
    return await chaine.repondre(instructions="i", question="q", format_sortie=Plan)


@pytest.mark.asyncio
async def test_le_premier_fournisseur_repond_et_les_suivants_ne_sont_pas_appeles():
    premier = FournisseurFactice("ovhcloud")
    second = FournisseurFactice("scaleway")

    reponse = await _demander(Rabattement([premier, second]))

    assert "ovhcloud" in reponse.contenu.sql
    assert second.appels == 0


@pytest.mark.asyncio
async def test_une_indisponibilite_fait_basculer_sur_le_fournisseur_suivant():
    premier = FournisseurFactice("ovhcloud", FournisseurIndisponible("ovhcloud", "erreur 503"))
    second = FournisseurFactice("scaleway")

    reponse = await _demander(Rabattement([premier, second]))

    assert "scaleway" in reponse.contenu.sql
    assert premier.appels == 1


@pytest.mark.asyncio
async def test_un_refus_du_modele_ne_declenche_aucun_rabattement():
    refus = ErreurUtilisateur("L'assistant a refuse de traiter cette demande.", code_http=422)
    premier = FournisseurFactice("ovhcloud", refus)
    second = FournisseurFactice("scaleway")

    with pytest.raises(ErreurUtilisateur) as leve:
        await _demander(Rabattement([premier, second]))

    assert leve.value.code_http == 422
    assert second.appels == 0, "un refus est un resultat, pas une panne : on ne rejoue pas ailleurs"


@pytest.mark.asyncio
async def test_tous_indisponibles_remonte_une_erreur_claire():
    chaine = Rabattement(
        [
            FournisseurFactice("ovhcloud", FournisseurIndisponible("ovhcloud", "delai depasse")),
            FournisseurFactice("scaleway", FournisseurIndisponible("scaleway", "erreur 500")),
        ]
    )

    with pytest.raises(ErreurUtilisateur) as leve:
        await _demander(chaine)

    assert leve.value.code_http == 503


def test_une_chaine_vide_est_refusee_a_la_construction():
    with pytest.raises(ValueError):
        Rabattement([])


# --- Le fournisseur compatible OpenAI, sans reseau ---------------------------


def _fournisseur(gestionnaire) -> FournisseurOpenAICompatible:
    return FournisseurOpenAICompatible(
        nom="ovhcloud",
        modele="gpt-oss-120b",
        cle_api="factice",
        http=httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire)),
    )


def _completion(contenu: str, entree: int = 900, sortie: int = 40) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": contenu}}],
            "usage": {"prompt_tokens": entree, "completion_tokens": sortie},
        },
    )


@pytest.mark.asyncio
async def test_la_sortie_structuree_est_relue_et_le_cout_calcule_au_tarif_du_fournisseur():
    fournisseur = _fournisseur(
        lambda requete: _completion('{"sql": "SELECT 1", "explication": "un"}')
    )

    reponse = await fournisseur.repondre(instructions="i", question="q", format_sortie=Plan)

    assert reponse.contenu.sql == "SELECT 1"
    assert reponse.consommation.tarif is OVH_GPT_OSS_120B
    attendu = (900 * 0.090 + 40 * 0.470) / 1_000_000
    assert reponse.consommation.cout_dollars == pytest.approx(attendu)


@pytest.mark.asyncio
async def test_le_schema_transmis_interdit_les_proprietes_supplementaires():
    vues = {}

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        vues.update(__import__("json").loads(requete.content))
        return _completion('{"sql": "SELECT 1", "explication": ""}')

    await _fournisseur(gestionnaire).repondre(instructions="i", question="q", format_sortie=Plan)

    schema = vues["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    # `explication` a une valeur par defaut cote Pydantic : le mode strict
    # exige qu'elle figure quand meme parmi les proprietes requises.
    assert set(schema["required"]) == {"sql", "explication"}


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [429, 500, 502, 503])
async def test_les_codes_de_panne_autorisent_le_rabattement(code):
    fournisseur = _fournisseur(lambda requete: httpx.Response(code, json={}))

    with pytest.raises(FournisseurIndisponible):
        await fournisseur.repondre(instructions="i", question="q", format_sortie=Plan)


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [401, 403])
async def test_une_cle_refusee_ne_declenche_pas_de_rabattement(code):
    fournisseur = _fournisseur(lambda requete: httpx.Response(code, json={}))

    # Notre configuration est fautive : le fournisseur suivant echouerait pareil.
    with pytest.raises(ErreurUtilisateur):
        await fournisseur.repondre(instructions="i", question="q", format_sortie=Plan)


@pytest.mark.asyncio
async def test_une_sortie_non_conforme_est_une_erreur_et_pas_une_panne():
    fournisseur = _fournisseur(lambda requete: _completion('{"pas_le_bon_champ": 1}'))

    with pytest.raises(ErreurUtilisateur) as leve:
        await fournisseur.repondre(instructions="i", question="q", format_sortie=Plan)

    assert leve.value.code_http == 502


@pytest.mark.asyncio
async def test_un_delai_depasse_est_une_panne():
    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("trop long", request=requete)

    with pytest.raises(FournisseurIndisponible):
        await _fournisseur(gestionnaire).repondre(
            instructions="i", question="q", format_sortie=Plan
        )


# --- Tarifs ------------------------------------------------------------------


def test_un_modele_sans_tarif_connu_est_refuse():
    """Un cout affiche a zero serait un mensonge : mieux vaut ne pas demarrer."""
    with pytest.raises(TarifInconnu):
        tarif_de("ovhcloud", "un-modele-jamais-tarife")


def test_le_tarif_par_defaut_reste_celui_du_fournisseur_historique():
    """Les consommations construites sans tarif gardent le comportement d'avant."""
    assert Consommation(1_000_000, 0, 0, 0).cout_dollars == pytest.approx(5.00)


@pytest.mark.asyncio
async def test_une_reponse_tronquee_le_dit_au_lieu_de_paraitre_malformee():
    """Constate en reel : le raisonnement de gpt-oss epuise le plafond de sortie."""

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"sql": "SELECT'}, "finish_reason": "length"}],
                "usage": {"prompt_tokens": 112, "completion_tokens": 300},
            },
        )

    with pytest.raises(ErreurUtilisateur) as leve:
        await _fournisseur(gestionnaire).repondre(
            instructions="i", question="q", format_sortie=Plan
        )

    assert "interrompu" in leve.value.message


# --- Routage par agent --------------------------------------------------------


class ReglagesFactices:
    """Le strict necessaire pour resoudre une chaine, sans lire l'environnement."""

    anthropic_api_key = "factice"
    ovhcloud_api_key = "factice"
    scaleway_api_key = "factice"
    ionos_api_key = "factice"

    def __init__(self, commune="", analyste="", redacteur="", viz=""):
        self.llm_chaine = commune
        self.llm_chaine_analyste = analyste
        self.llm_chaine_redacteur = redacteur
        self.llm_chaine_viz = viz


def _chaine(monkeypatch, reglages, agent=""):
    from app.core import llm_client

    monkeypatch.setattr(llm_client, "get_settings", lambda: reglages)
    return llm_client.construire_la_chaine(agent).noms


def test_sans_chaine_declaree_on_garde_le_fournisseur_historique(monkeypatch):
    assert _chaine(monkeypatch, ReglagesFactices()) == ["anthropic/claude-opus-5"]


def test_un_agent_sans_chaine_propre_utilise_la_chaine_commune(monkeypatch):
    reglages = ReglagesFactices(commune="ovhcloud:gpt-oss-120b")
    assert _chaine(monkeypatch, reglages, "redacteur") == ["ovhcloud/gpt-oss-120b"]


def test_un_agent_avec_sa_chaine_propre_la_prefere(monkeypatch):
    reglages = ReglagesFactices(
        commune="ovhcloud:gpt-oss-120b", analyste="ovhcloud:Qwen3.5-397B-A17B"
    )
    assert _chaine(monkeypatch, reglages, "analyste") == ["ovhcloud/Qwen3.5-397B-A17B"]
    assert _chaine(monkeypatch, reglages, "viz") == ["ovhcloud/gpt-oss-120b"]


def test_un_agent_inconnu_retombe_sur_la_chaine_commune(monkeypatch):
    """Oublier de declarer un agent ne doit pas l'envoyer sur un modele au hasard."""
    reglages = ReglagesFactices(commune="ovhcloud:gpt-oss-120b", analyste="ionos:gpt-oss-120b")
    assert _chaine(monkeypatch, reglages, "agent_qui_n_existe_pas") == ["ovhcloud/gpt-oss-120b"]


def test_le_rabattement_par_agent_garde_le_meme_modele_chez_trois_hebergeurs(monkeypatch):
    reglages = ReglagesFactices(
        analyste="ovhcloud:gpt-oss-120b,scaleway:gpt-oss-120b,ionos:gpt-oss-120b"
    )
    noms = _chaine(monkeypatch, reglages, "analyste")
    assert [n.split("/")[0] for n in noms] == ["ovhcloud", "scaleway", "ionos"]
    assert len({n.split("/")[1] for n in noms}) == 1, "un rabattement ne change pas de modele"
