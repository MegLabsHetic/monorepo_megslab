"""Enchaine plusieurs fournisseurs de modele, du prefere au dernier recours.

La regle tient en une phrase : on rabat sur une panne de DISPONIBILITE, jamais
sur un defaut de CONTENU.

Un rabattement declenche par un refus du modele ou par une sortie mal formee
transformerait ce mecanisme de robustesse en machine a dissimuler les defauts.
Le produit affiche le SQL qu'il execute et le cout qu'il paie ; il ne va pas
cacher qu'un modele est inadapte en rejouant discretement la question ailleurs.

C'est pourquoi seule `FournisseurIndisponible` autorise l'essai suivant : toute
autre erreur remonte immediatement.
"""

import logging

from pydantic import BaseModel

from app.core.consommation import Reponse
from app.core.errors import ErreurUtilisateur, FournisseurIndisponible

logger = logging.getLogger(__name__)


class Rabattement:
    """Une chaine de fournisseurs essayes dans l'ordre."""

    def __init__(self, fournisseurs: list) -> None:
        if not fournisseurs:
            raise ValueError("Une chaine de rabattement a besoin d'au moins un fournisseur.")
        self._fournisseurs = fournisseurs

    @property
    def noms(self) -> list[str]:
        return [f.nom for f in self._fournisseurs]

    async def repondre[T: BaseModel](
        self,
        *,
        instructions: str,
        question: str,
        format_sortie: type[T],
        effort: str = "medium",
    ) -> Reponse[T]:
        pannes: list[str] = []
        for rang, fournisseur in enumerate(self._fournisseurs, 1):
            try:
                reponse = await fournisseur.repondre(
                    instructions=instructions,
                    question=question,
                    format_sortie=format_sortie,
                    effort=effort,
                )
            except FournisseurIndisponible as panne:
                pannes.append(f"{fournisseur.nom} ({panne.raison})")
                logger.warning(
                    "Rabattement %s/%s : %s indisponible (%s)",
                    rang,
                    len(self._fournisseurs),
                    fournisseur.nom,
                    panne.raison,
                )
                continue
            if rang > 1:
                logger.info("Repondu par le fournisseur de secours %s", fournisseur.nom)
            return reponse

        # Tous indisponibles : c'est une panne, et elle se dit comme telle.
        logger.error("Aucun fournisseur disponible : %s", " ; ".join(pannes))
        raise ErreurUtilisateur(
            "L'assistant est momentanement injoignable. Reessayez dans un instant.",
            code_http=503,
        )
