"""Appels au modele chez un fournisseur exposant une API compatible OpenAI.

Une seule classe couvre OVHcloud, Scaleway et IONOS : les trois exposent le
meme contrat sur /v1/chat/completions, et ne different que par leur URL de
base, leur cle et le nom du modele. Ecrire trois classes identiques a l'URL
pres n'apporterait rien.

Le SDK officiel n'est pas utilise : httpx est deja une dependance, et le client
Airbyte montre que ca se teste sans reseau avec MockTransport. Une dependance
de moins pour un contrat HTTP de cette taille.
"""

import logging
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.consommation import Consommation, Reponse
from app.core.errors import ErreurUtilisateur, FournisseurIndisponible
from app.core.tarifs import Tarif, tarif_de

logger = logging.getLogger(__name__)

MAX_JETONS_SORTIE = 8000
DELAI_SECONDES = 45.0

# Les URL de base relevees le 9 septembre 2026. Le chemin /v1 est inclus :
# les trois fournisseurs le placent au meme endroit.
URLS_DE_BASE = {
    "ovhcloud": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
    "scaleway": "https://api.scaleway.ai/v1",
    "ionos": "https://openai.inference.de-txl.ionos.com/v1",
}


class FournisseurOpenAICompatible:
    """Un modele servi par une API compatible OpenAI, en sortie structuree."""

    def __init__(
        self,
        *,
        nom: str,
        modele: str,
        cle_api: str = "",
        url_de_base: str = "",
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._nom = nom
        self._modele = modele
        self._cle_api = cle_api
        self._url_de_base = (url_de_base or URLS_DE_BASE.get(nom, "")).rstrip("/")
        self._http = http
        self._tarif: Tarif = tarif_de(nom, modele)

    @property
    def nom(self) -> str:
        return f"{self._nom}/{self._modele}"

    async def repondre[T: BaseModel](
        self,
        *,
        instructions: str,
        question: str,
        format_sortie: type[T],
        effort: str = "medium",
    ) -> Reponse[T]:
        """Pose une question et rend une reponse deja conforme au schema demande.

        `effort` est ignore : aucun de ces fournisseurs n'expose de reglage
        equivalent. L'arbitrage cout/qualite s'y fait en choisissant le modele.
        """
        charge = self._charge_utile(instructions, question, format_sortie)
        donnees = await self._envoyer(charge)
        return Reponse(
            contenu=self._lire_contenu(donnees, format_sortie),
            consommation=self._consommation(donnees.get("usage") or {}),
        )

    def _charge_utile(self, instructions: str, question: str, format_sortie: type) -> dict:
        return {
            "model": self._modele,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": question},
            ],
            "max_tokens": MAX_JETONS_SORTIE,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": format_sortie.__name__.lower(),
                    "strict": True,
                    "schema": _schema_strict(format_sortie),
                },
            },
        }

    async def _envoyer(self, charge: dict) -> dict:
        if not self._cle_api and self._http is None:
            raise ErreurUtilisateur(
                f"Le fournisseur {self._nom} n'est pas configure sur ce serveur.", code_http=503
            )
        client = self._http or httpx.AsyncClient(timeout=DELAI_SECONDES)
        try:
            reponse = await client.post(
                f"{self._url_de_base}/chat/completions",
                json=charge,
                headers={"Authorization": f"Bearer {self._cle_api}"},
            )
        except httpx.TimeoutException as erreur:
            raise FournisseurIndisponible(self._nom, "delai depasse") from erreur
        except httpx.HTTPError as erreur:
            raise FournisseurIndisponible(self._nom, "injoignable") from erreur
        finally:
            if self._http is None:
                await client.aclose()
        self._verifier_le_code(reponse)
        return reponse.json()

    def _verifier_le_code(self, reponse: httpx.Response) -> None:
        """Distingue ce qui merite un rabattement de ce qui vient de nous.

        Un 401 ou un 400 se reproduira a l'identique chez le fournisseur
        suivant : y rabattre ferait perdre du temps sans rien reparer.
        """
        if reponse.is_success:
            return
        code = reponse.status_code
        if code in (401, 403):
            logger.error("Cle refusee par %s", self._nom)
            raise ErreurUtilisateur(
                f"Le fournisseur {self._nom} n'est pas configure correctement.", code_http=503
            )
        if code == 429 or code >= 500:
            logger.warning("%s indisponible (HTTP %s)", self._nom, code)
            raise FournisseurIndisponible(self._nom, f"erreur {code}")
        logger.error("Requete refusee par %s (HTTP %s) : %s", self._nom, code, reponse.text[:300])
        raise ErreurUtilisateur("L'assistant est momentanement indisponible.", code_http=503)

    def _lire_contenu[T: BaseModel](self, donnees: dict, format_sortie: type[T]) -> T:
        """Une sortie mal formee est un defaut du modele, pas une panne du serveur.

        On ne rabat donc pas : le fournisseur a repondu, sa reponse est
        mauvaise, et le masquer derriere un autre fournisseur reviendrait a
        cacher un modele inadapte a la tache.
        """
        self._refuser_si_tronque(donnees)
        try:
            brut = donnees["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as erreur:
            logger.error("Reponse inattendue de %s : %s", self._nom, str(donnees)[:300])
            raise ErreurUtilisateur(
                "L'assistant a renvoye une reponse inexploitable.", code_http=502
            ) from erreur
        try:
            return format_sortie.model_validate_json(brut)
        except ValidationError as erreur:
            logger.error("Sortie non conforme au schema chez %s : %s", self._nom, str(brut)[:300])
            raise ErreurUtilisateur(
                "L'assistant a renvoye une reponse inexploitable.", code_http=502
            ) from erreur

    def _refuser_si_tronque(self, donnees: dict) -> None:
        """Une reponse coupee net produit un JSON invalide, au message trompeur.

        Constate en reel le 9 septembre 2026 sur gpt-oss-120b : ces modeles
        emettent un champ `reasoning` facture parmi les jetons de sortie, qui
        consomme le plafond avant meme que la reponse commence. Sans ce
        controle, l'utilisateur lirait « reponse inexploitable » alors que le
        defaut est un plafond trop bas.
        """
        choix = (donnees.get("choices") or [{}])[0]
        if choix.get("finish_reason") != "length":
            return
        logger.error(
            "Reponse tronquee par %s : plafond de %s jetons atteint", self._nom, MAX_JETONS_SORTIE
        )
        raise ErreurUtilisateur(
            "L'assistant a ete interrompu avant d'avoir fini de repondre.", code_http=502
        )

    def _consommation(self, usage: dict) -> Consommation:
        """Aucun de ces fournisseurs ne facture de cache : les compteurs restent a zero.

        Le raisonnement emis par certains modeles ouverts est compte dans
        `completion_tokens` : il est donc facture, et le compteur le reflete.
        """
        return Consommation(
            jetons_entree=int(usage.get("prompt_tokens") or 0),
            jetons_sortie=int(usage.get("completion_tokens") or 0),
            jetons_cache_lus=0,
            jetons_cache_ecrits=0,
            tarif=self._tarif,
        )


def _schema_strict(format_sortie: type[BaseModel]) -> dict[str, Any]:
    """Rend un schema Pydantic acceptable par le mode strict d'OpenAI.

    Le mode strict exige que chaque objet interdise les proprietes
    supplementaires et declare toutes ses proprietes comme requises — y
    compris celles qui ont une valeur par defaut cote Pydantic, que le schema
    genere omet du tableau `required`.
    """
    schema = format_sortie.model_json_schema()
    _durcir(schema)
    return schema


def _durcir(noeud: Any) -> None:
    if isinstance(noeud, list):
        for element in noeud:
            _durcir(element)
        return
    if not isinstance(noeud, dict):
        return
    if noeud.get("type") == "object" and "properties" in noeud:
        noeud["additionalProperties"] = False
        noeud["required"] = list(noeud["properties"])
    for valeur in noeud.values():
        _durcir(valeur)
