"""Donne (ou retire) le role d'operateur de la plateforme a un compte.

Volontairement hors de l'API : aucun utilisateur, meme proprietaire d'une
organisation, ne peut se promouvoir operateur depuis l'interface. Seul
quelqu'un qui a la main sur le serveur le peut.

    python -m app.scripts.promouvoir_super_admin ada@example.com
    python -m app.scripts.promouvoir_super_admin ada@example.com --retirer
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import creer_session

# Les modeles se referencent par nom : tous doivent etre charges avant la
# premiere requete, sinon le mapper de User ne trouve pas « Membership ».
from app.models import (  # noqa: F401
    conversation,
    data_source,
    invitation,
    membership,
    organization,
    question,
    workspace,
    workspace_access,
)
from app.models.user import User


async def _basculer(email: str, valeur: bool) -> None:
    async with creer_session() as db:
        utilisateur = (
            await db.execute(select(User).where(User.email == email.strip().lower()))
        ).scalar_one_or_none()
        if utilisateur is None:
            print(f"Aucun compte avec l'e-mail {email}.")
            sys.exit(1)
        utilisateur.est_super_admin = valeur
        await db.commit()
        etat = "est desormais operateur de la plateforme" if valeur else "n'est plus operateur"
        print(f"{utilisateur.nom_complet} <{utilisateur.email}> {etat}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    asyncio.run(_basculer(sys.argv[1], "--retirer" not in sys.argv))
