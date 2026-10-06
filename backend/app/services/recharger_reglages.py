"""Porte les reglages de la base vers le client de modele.

Appele au demarrage et apres chaque ecriture. Isole ici pour que ni le service
de reglages ni le client de modele n'aient a connaitre l'autre.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import creer_session
from app.core.llm_client import appliquer_surcharges
from app.core.secrets_chiffres import SecretIllisible, dechiffrer
from app.services.reglages_llm_service import ReglagesLLMService

logger = logging.getLogger(__name__)


async def recharger(db: AsyncSession) -> int:
    """Relit la base et applique ses valeurs. Rend le nombre de surcharges."""
    valeurs = await ReglagesLLMService(db).tout_lire()
    resultat = {}
    for cle, valeur in valeurs.items():
        if not valeur:
            continue
        if cle.startswith("cle:"):
            try:
                resultat[cle] = dechiffrer(valeur)
            except SecretIllisible:
                logger.error("Reglage %s illisible : SECRET_CHIFFREMENT a change", cle)
            continue
        resultat[cle] = valeur
    appliquer_surcharges(resultat)
    return len(resultat)


async def recharger_au_demarrage() -> None:
    """Sans base joignable, on garde l'environnement plutot que d'empecher le demarrage."""
    try:
        async with creer_session() as db:
            await recharger(db)
    except Exception:  # noqa: BLE001
        logger.exception("Reglages non relus au demarrage : l'environnement s'applique")
