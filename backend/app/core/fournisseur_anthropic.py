"""Appels au modele chez Anthropic.

Ce fournisseur est le seul a exposer deux leviers qui n'existent pas ailleurs :
la mise en cache des instructions, et un niveau d'effort par appel. Ils sont
conserves ici plutot que hisses dans une abstraction commune — les autres
fournisseurs n'en ont pas d'equivalent, et une option qui ne veut rien dire
pour la moitie des implementations est une option a ne pas creer.
"""

import logging

import anthropic
from pydantic import BaseModel

from app.core.consommation import Consommation, Reponse
from app.core.errors import ErreurUtilisateur, FournisseurIndisponible
from app.core.tarifs import Tarif, tarif_de

logger = logging.getLogger(__name__)

NOM = "anthropic"
MODELE_PAR_DEFAUT = "claude-opus-5"
MAX_JETONS_SORTIE = 8000


class FournisseurAnthropic:
    """Un modele Anthropic, interroge en sortie structuree."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic | None = None,
        cle_api: str = "",
        modele: str = MODELE_PAR_DEFAUT,
    ) -> None:
        self._client = client
        self._cle_api = cle_api
        self._modele = modele
        self._tarif: Tarif = tarif_de(NOM, modele)

    @property
    def nom(self) -> str:
        return f"{NOM}/{self._modele}"

    async def repondre[T: BaseModel](
        self,
        *,
        instructions: str,
        question: str,
        format_sortie: type[T],
        effort: str = "medium",
    ) -> Reponse[T]:
        """Pose une question et rend une reponse deja conforme au schema demande.

        Les instructions sont mises en cache : elles ne changent pas d'une
        question a l'autre, contrairement a la question elle-meme.
        """
        client = self._anthropic()
        reponse = await self._appeler(client, instructions, question, format_sortie, effort)
        self._refuser_si_refus(reponse)
        return Reponse(
            contenu=reponse.parsed_output, consommation=self._consommation(reponse.usage)
        )

    def _anthropic(self) -> anthropic.AsyncAnthropic:
        """Construit le client au premier appel, pas a l'import.

        Lire la cle a l'import figerait la configuration au demarrage du
        processus, et ferait echouer l'import quand aucune cle n'est posee —
        y compris dans les tests, qui n'en ont pas besoin.
        """
        if self._client is None:
            if not self._cle_api:
                raise ErreurUtilisateur(
                    "L'assistant n'est pas configure sur ce serveur.", code_http=503
                )
            self._client = anthropic.AsyncAnthropic(api_key=self._cle_api)
        return self._client

    async def _appeler(self, client, instructions, question, format_sortie, effort):
        try:
            return await client.messages.parse(
                model=self._modele,
                max_tokens=MAX_JETONS_SORTIE,
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
            # Notre faute, pas une panne : le fournisseur suivant echouerait
            # tout autant si la configuration est incomplete.
            logger.exception("Cle Anthropic refusee")
            raise ErreurUtilisateur(
                "L'assistant n'est pas configure correctement sur ce serveur.", code_http=503
            ) from erreur
        except anthropic.RateLimitError as erreur:
            logger.warning("Limite de debit atteinte chez Anthropic")
            raise FournisseurIndisponible(NOM, "limite de debit atteinte") from erreur
        except anthropic.APIStatusError as erreur:
            logger.warning("Erreur %s renvoyee par Anthropic", erreur.status_code)
            raise FournisseurIndisponible(NOM, f"erreur {erreur.status_code}") from erreur
        except anthropic.APIConnectionError as erreur:
            logger.warning("Anthropic injoignable")
            raise FournisseurIndisponible(NOM, "injoignable") from erreur

    def _refuser_si_refus(self, reponse) -> None:
        """Un refus du modele est un resultat, pas une panne : on ne rabat pas."""
        if reponse.stop_reason != "refusal":
            return
        categorie = reponse.stop_details.category if reponse.stop_details else "inconnue"
        logger.warning("Le modele a refuse de repondre (categorie %s)", categorie)
        raise ErreurUtilisateur("L'assistant a refuse de traiter cette demande.", code_http=422)

    def _consommation(self, usage) -> Consommation:
        """Les champs de cache valent None quand aucun cache n'est en jeu."""
        return Consommation(
            jetons_entree=usage.input_tokens,
            jetons_sortie=usage.output_tokens,
            jetons_cache_lus=usage.cache_read_input_tokens or 0,
            jetons_cache_ecrits=usage.cache_creation_input_tokens or 0,
            tarif=self._tarif,
        )
