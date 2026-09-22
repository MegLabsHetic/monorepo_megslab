"""Lit et ecrit la configuration des modeles, base d'abord, environnement ensuite.

La regle tient en une phrase : **ce qui est en base l'emporte, ce qui est vide
retombe sur l'environnement.** Vider un reglage depuis l'interface rend donc
exactement le comportement du fichier de deploiement - il n'y a pas d'etat
intermediaire ou personne ne saurait plus ce qui s'applique.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur
from app.core.secrets_chiffres import SecretIllisible, chiffrer, dechiffrer, masquer
from app.models.configuration_llm import AGENTS, FOURNISSEURS, ReglageLLM, cle_api, cle_chaine

logger = logging.getLogger(__name__)

# Correspondance avec les variables d'environnement, pour le repli.
ENV_CHAINES = {
    "analyste": "llm_chaine_analyste",
    "redacteur": "llm_chaine_redacteur",
    "viz": "llm_chaine_viz",
}
ENV_CLES = {
    "anthropic": "anthropic_api_key",
    "ovhcloud": "ovhcloud_api_key",
    "scaleway": "scaleway_api_key",
    "ionos": "ionos_api_key",
}


class ReglagesLLMService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def tout_lire(self) -> dict[str, str]:
        resultat = await self._db.execute(select(ReglageLLM))
        return {r.cle: r.valeur for r in resultat.scalars()}

    async def chaine_de(self, agent: str, brut: dict[str, str] | None = None) -> tuple[str, str]:
        """La chaine de cet agent, et d'ou elle vient : « base » ou « environnement »."""
        valeurs = brut if brut is not None else await self.tout_lire()
        posee = valeurs.get(cle_chaine(agent), "").strip()
        if posee:
            return posee, "base"
        reglages = get_settings()
        depuis_env = getattr(reglages, ENV_CHAINES.get(agent, ""), "") or reglages.llm_chaine
        return (depuis_env or "").strip(), "environnement"

    async def cle_de(self, fournisseur: str, brut: dict[str, str] | None = None) -> tuple[str, str]:
        """La cle de ce fournisseur, en clair, et son origine."""
        valeurs = brut if brut is not None else await self.tout_lire()
        chiffree = valeurs.get(cle_api(fournisseur), "")
        if chiffree:
            try:
                return dechiffrer(chiffree), "base"
            except SecretIllisible:
                logger.error("Cle %s illisible : SECRET_CHIFFREMENT a change", fournisseur)
                return "", "illisible"
        return getattr(get_settings(), ENV_CLES.get(fournisseur, ""), "") or "", "environnement"

    async def poser_chaine(self, agent: str, chaine: str) -> None:
        if agent not in AGENTS:
            raise ErreurUtilisateur(f"Agent inconnu : « {agent} ».", code_http=422)
        await self._ecrire(cle_chaine(agent), chaine.strip(), secret=False)

    async def poser_cle(self, fournisseur: str, cle: str) -> None:
        if fournisseur not in FOURNISSEURS:
            raise ErreurUtilisateur(f"Fournisseur inconnu : « {fournisseur} ».", code_http=422)
        cle = cle.strip()
        await self._ecrire(cle_api(fournisseur), chiffrer(cle) if cle else "", secret=bool(cle))

    async def etat_des_cles(self) -> dict[str, dict]:
        """Ce que l'interface a le droit de voir : jamais la cle, seulement son empreinte."""
        valeurs = await self.tout_lire()
        etat = {}
        for fournisseur in FOURNISSEURS:
            claire, origine = await self.cle_de(fournisseur, valeurs)
            etat[fournisseur] = {
                "definie": bool(claire),
                "origine": origine,
                "empreinte": masquer(claire),
            }
        return etat

    async def _ecrire(self, cle: str, valeur: str, secret: bool) -> None:
        resultat = await self._db.execute(select(ReglageLLM).where(ReglageLLM.cle == cle))
        reglage = resultat.scalar_one_or_none()
        if reglage is None:
            if not valeur:
                return
            self._db.add(ReglageLLM(cle=cle, valeur=valeur, secret=secret))
        else:
            reglage.valeur = valeur
            reglage.secret = secret
        await self._db.commit()
