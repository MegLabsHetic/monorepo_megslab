"""Appels au modele, avec comptage de ce qu'ils coutent.

Un seul point de passage vers Anthropic. Chaque appel rend, en plus de sa
reponse, les jetons consommes et leur cout : afficher au jury ce qu'une analyse
a coute suppose de le mesurer a la source, pas de l'estimer apres coup.

Le choix du modele n'appartient pas aux agents. Il est declare ici, par tache,
pour que l'arbitrage cout/qualite se relise en un seul endroit.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur

logger = logging.getLogger(__name__)

MODELE = "claude-opus-5"

# Tarifs Anthropic en dollars par million de jetons, releves dans la
# documentation de l'API. Une lecture en cache coute environ un dixieme d'une
# lecture normale, une ecriture environ 1,25 fois.
#
# ATTENTION : un tarif perime fausse le compteur qu'on montre. A reverifier
# avant toute demonstration.
PRIX_ENTREE = 5.00
PRIX_SORTIE = 25.00
PRIX_CACHE_LECTURE = 0.50
PRIX_CACHE_ECRITURE = 6.25

_MILLION = 1_000_000

Sortie = TypeVar("Sortie", bound=BaseModel)


@dataclass(frozen=True)
class Consommation:
    """Ce qu'un appel a consomme, et ce qu'il a coute."""

    jetons_entree: int
    jetons_sortie: int
    jetons_cache_lus: int
    jetons_cache_ecrits: int

    @property
    def cout_dollars(self) -> float:
        return (
            self.jetons_entree * PRIX_ENTREE
            + self.jetons_sortie * PRIX_SORTIE
            + self.jetons_cache_lus * PRIX_CACHE_LECTURE
            + self.jetons_cache_ecrits * PRIX_CACHE_ECRITURE
        ) / _MILLION

    @property
    def jetons_total(self) -> int:
        return (
            self.jetons_entree
            + self.jetons_sortie
            + self.jetons_cache_lus
            + self.jetons_cache_ecrits
        )


@dataclass(frozen=True)
class Reponse[T: BaseModel]:
    """Une reponse structuree, accompagnee de ce qu'elle a coute."""

    contenu: T
    consommation: Consommation


class LLMClient:
    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        self._client = client

    def _anthropic(self) -> anthropic.AsyncAnthropic:
        """Construit le client au premier appel, pas a l'import.

        Lire la cle a l'import figerait la configuration au demarrage du
        processus, et ferait echouer l'import quand aucune cle n'est posee —
        y compris dans les tests, qui n'en ont pas besoin.
        """
        if self._client is None:
            cle = get_settings().anthropic_api_key
            if not cle:
                raise ErreurUtilisateur(
                    "L'assistant n'est pas configure sur ce serveur.", code_http=503
                )
            self._client = anthropic.AsyncAnthropic(api_key=cle)
        return self._client

    async def repondre(
        self,
        *,
        instructions: str,
        question: str,
        format_sortie: type[Sortie],
        effort: str = "medium",
    ) -> Reponse[Sortie]:
        """Pose une question au modele et rend une reponse deja validee.

        `format_sortie` contraint la sortie a un schema : le modele ne peut pas
        repondre a cote de la structure attendue, ce qui evite d'ecrire un
        analyseur de texte libre pour recuperer du SQL.

        Les instructions sont mises en cache : elles ne changent pas d'une
        question a l'autre, contrairement a la question elle-meme.
        """
        client = self._anthropic()
        try:
            reponse = await client.messages.parse(
                model=MODELE,
                max_tokens=8000,
                system=[
                    {
                        "type": "text",
                        "text": instructions,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": question}],
                output_format=format_sortie,
                thinking={"type": "adaptive"},
                output_config={"effort": effort},
            )
        except anthropic.AuthenticationError as erreur:
            logger.exception("Cle Anthropic refusee")
            raise ErreurUtilisateur(
                "L'assistant n'est pas configure correctement sur ce serveur.", code_http=503
            ) from erreur
        except anthropic.RateLimitError as erreur:
            logger.warning("Limite de debit atteinte chez Anthropic")
            raise ErreurUtilisateur(
                "L'assistant recoit trop de demandes. Reessayez dans un instant.", code_http=429
            ) from erreur
        except anthropic.APIStatusError as erreur:
            logger.exception("Erreur %s renvoyee par Anthropic", erreur.status_code)
            raise ErreurUtilisateur(
                "L'assistant est momentanement indisponible.", code_http=503
            ) from erreur
        except anthropic.APIConnectionError as erreur:
            logger.exception("Anthropic injoignable")
            raise ErreurUtilisateur(
                "L'assistant est momentanement injoignable.", code_http=503
            ) from erreur

        if reponse.stop_reason == "refusal":
            categorie = reponse.stop_details.category if reponse.stop_details else "inconnue"
            logger.warning("Le modele a refuse de repondre (categorie %s)", categorie)
            raise ErreurUtilisateur("L'assistant a refuse de traiter cette demande.", code_http=422)

        return Reponse(contenu=reponse.parsed_output, consommation=_consommation(reponse.usage))


@lru_cache
def get_llm_client() -> LLMClient:
    """Dependance FastAPI : un client par processus, remplacable dans les tests."""
    return LLMClient()


def _consommation(usage) -> Consommation:
    """Les champs de cache valent None quand aucun cache n'est en jeu."""
    return Consommation(
        jetons_entree=usage.input_tokens,
        jetons_sortie=usage.output_tokens,
        jetons_cache_lus=usage.cache_read_input_tokens or 0,
        jetons_cache_ecrits=usage.cache_creation_input_tokens or 0,
    )
