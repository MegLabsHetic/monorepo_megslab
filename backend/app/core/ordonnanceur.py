"""La brique qui manquait : quelque chose qui se declenche sans qu'on le demande.

Jusqu'ici, la seule planification du produit etait celle d'Airbyte. Rien, cote
application, ne tournait de lui-meme. Cet ordonnanceur est volontairement
minuscule : une boucle asyncio qui se reveille chaque heure et execute les
surveillances dont c'est l'heure.

Pourquoi pas de bibliotheque de planification : une dependance de plus pour
une boucle de vingt lignes, alors qu'il n'y a qu'un seul type de tache et une
seule granularite - l'heure. Le jour ou il faudra des expressions cron et de
la reprise sur panne, cette boucle devra ceder la place, et c'est ecrit ici
pour que personne ne l'etire au-dela de ce qu'elle sait faire.

DEUX LIMITES, a connaitre avant de s'y fier :

1. Le compteur vit dans le processus. Avec plusieurs repliques du backend,
   chaque replique executerait les memes surveillances - donc autant de
   notifications que de repliques. Il faudra un verrou partage avant de passer
   a l'echelle.
2. Un redemarrage pendant l'heure creuse saute le tour. On ne rattrape pas :
   une alerte en retard de vingt-trois heures vaut moins que pas d'alerte.

L'ordonnanceur est **eteint par defaut**. Sans ORDONNANCEUR_ACTIF, le backend
se comporte exactement comme avant.
"""

import asyncio
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# On se reveille plus souvent que l'heure pour que le demarrage n'attende pas
# soixante minutes avant son premier tour.
PERIODE_SECONDES = 600


class Ordonnanceur:
    """Reveille une tache une fois par heure, au plus."""

    def __init__(self, tache, horloge=lambda: datetime.now(UTC)) -> None:
        self._tache = tache
        self._horloge = horloge
        self._derniere_heure: int | None = None
        self._boucle: asyncio.Task | None = None

    async def tour(self) -> bool:
        """Execute la tache si l'heure a change depuis le dernier tour.

        Rend vrai quand la tache a tourne. Separee de la boucle pour qu'un test
        puisse la declencher sans attendre.
        """
        heure = self._horloge().hour
        if heure == self._derniere_heure:
            return False
        self._derniere_heure = heure
        try:
            await self._tache(heure)
        except Exception:  # noqa: BLE001
            # Une tache qui echoue ne doit pas emporter la boucle : sinon une
            # surveillance mal ecrite arreterait toutes les autres, en silence.
            logger.exception("Le tour d'ordonnancement de %s h a echoue", heure)
        return True

    async def _boucler(self) -> None:
        while True:
            await self.tour()
            await asyncio.sleep(PERIODE_SECONDES)

    def demarrer(self) -> None:
        if self._boucle is None:
            self._boucle = asyncio.create_task(self._boucler())
            logger.info("Ordonnanceur demarre (reveil toutes les %s s)", PERIODE_SECONDES)

    async def arreter(self) -> None:
        if self._boucle is None:
            return
        self._boucle.cancel()
        try:
            await self._boucle
        except asyncio.CancelledError:
            pass
        self._boucle = None
        logger.info("Ordonnanceur arrete")
