"""Point de passage unique des agents vers un modele de langage.

Les agents ne savent pas quel fournisseur repond, ni combien il y en a. Ils
appellent `repondre` et recoivent une reponse structuree accompagnee de son
cout reel — chez celui qui a effectivement repondu.

La chaine de fournisseurs se declare dans la configuration, pas dans le code :

    LLM_CHAINE=ovhcloud:gpt-oss-120b,scaleway:gpt-oss-120b,ionos:gpt-oss-120b

Le meme modele chez trois hebergeurs differents : un rabattement change d'hote
sans changer ce que l'utilisateur recoit. Rabattre sur un AUTRE modele ferait
varier silencieusement la qualite des reponses, ce que ce produit s'interdit.
"""

import logging
from functools import lru_cache

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.consommation import Consommation, Reponse
from app.core.errors import ErreurUtilisateur
from app.core.fournisseur_anthropic import FournisseurAnthropic
from app.core.fournisseur_openai import FournisseurOpenAICompatible
from app.core.rabattement import Rabattement

logger = logging.getLogger(__name__)

__all__ = ["Consommation", "Reponse", "LLMClient", "get_llm_client"]

CHAINE_PAR_DEFAUT = "anthropic:claude-opus-5"


class LLMClient:
    """Interroge le modele, ou le suivant de la chaine s'il est indisponible."""

    def __init__(self, chaine: Rabattement | None = None) -> None:
        self._chaine = chaine
        self._par_agent: dict[str, Rabattement] = {}

    async def repondre[T: BaseModel](
        self,
        *,
        instructions: str,
        question: str,
        format_sortie: type[T],
        effort: str = "medium",
        agent: str = "",
    ) -> Reponse[T]:
        """Pose une question au modele et rend une reponse deja validee.

        `format_sortie` contraint la sortie a un schema : le modele ne peut pas
        repondre a cote de la structure attendue, ce qui evite d'ecrire un
        analyseur de texte libre pour recuperer du SQL.

        `agent` permet de router chaque agent vers sa propre chaine. Absent ou
        inconnu, la chaine commune s'applique : un agent qu'on oublie de
        declarer garde le comportement d'avant, il ne tombe pas sur un modele
        au hasard.
        """
        return await self._resoudre(agent).repondre(
            instructions=instructions,
            question=question,
            format_sortie=format_sortie,
            effort=effort,
        )

    def _resoudre(self, agent: str = "") -> Rabattement:
        """Construit la chaine de cet agent au premier appel, pas a l'import.

        Lire la configuration a l'import la figerait au demarrage du processus
        et ferait echouer l'import quand aucune cle n'est posee — y compris
        dans les tests, qui n'en ont pas besoin.
        """
        # Une chaine injectee au constructeur vaut pour tous les agents : c'est
        # ce dont les tests ont besoin, et ca reste explicite.
        if self._chaine is not None:
            return self._chaine
        cle = agent.strip().lower()
        if cle not in self._par_agent:
            self._par_agent[cle] = construire_la_chaine(cle)
        return self._par_agent[cle]


# La chaine propre a chaque agent, si elle est declaree.
CHAINES_PAR_AGENT = {
    "analyste": "llm_chaine_analyste",
    "redacteur": "llm_chaine_redacteur",
    "viz": "llm_chaine_viz",
}


def construire_la_chaine(agent: str = "") -> Rabattement:
    """Traduit la chaine de cet agent en fournisseurs, dans l'ordre declare.

    Ordre de resolution : la chaine de l'agent, sinon la chaine commune, sinon
    le fournisseur historique. Un agent sans chaine propre ne change donc pas
    de comportement.
    """
    reglages = get_settings()
    propre = getattr(reglages, CHAINES_PAR_AGENT.get(agent, ""), "") if agent else ""
    declaration = propre or reglages.llm_chaine or CHAINE_PAR_DEFAUT
    etapes = [e.strip() for e in declaration.split(",") if e.strip()]
    fournisseurs = [_fournisseur(etape, reglages) for etape in etapes]
    if propre or len(fournisseurs) > 1:
        logger.info(
            "Chaine %s : %s",
            agent or "commune",
            " -> ".join(f.nom for f in fournisseurs),
        )
    return Rabattement(fournisseurs)


def _fournisseur(etape: str, reglages):
    nom, _, modele = etape.partition(":")
    nom, modele = nom.strip().lower(), modele.strip()
    if not modele:
        raise ErreurUtilisateur(
            f"LLM_CHAINE mal formee : « {etape} ». Attendu « fournisseur:modele ».",
            code_http=503,
        )
    if nom == "anthropic":
        return FournisseurAnthropic(cle_api=reglages.anthropic_api_key, modele=modele)
    return FournisseurOpenAICompatible(
        nom=nom, modele=modele, cle_api=_cle(nom, reglages), http=_http_partage()
    )


def _cle(nom: str, reglages) -> str:
    cles = {
        "ovhcloud": reglages.ovhcloud_api_key,
        "scaleway": reglages.scaleway_api_key,
        "ionos": reglages.ionos_api_key,
    }
    if nom not in cles:
        raise ErreurUtilisateur(f"Fournisseur inconnu dans LLM_CHAINE : « {nom} ».", code_http=503)
    return cles[nom]


@lru_cache
def _http_partage() -> httpx.AsyncClient:
    """Un seul client HTTP pour toute la chaine : les connexions se reutilisent.

    En ouvrir un par appel couterait une poignee de main TLS a chaque question,
    sur un chemin ou l'on compte deja les secondes.
    """
    from app.core.fournisseur_openai import DELAI_SECONDES

    return httpx.AsyncClient(timeout=DELAI_SECONDES)


@lru_cache
def get_llm_client() -> LLMClient:
    """Dependance FastAPI : un client par processus, remplacable dans les tests."""
    return LLMClient()
