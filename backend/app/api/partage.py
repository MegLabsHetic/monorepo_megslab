"""Un tableau de bord rendu public par un lien, sans compte ni mot de passe.

C'est la seule route du produit qui ne demande aucune authentification. Trois
consequences, toutes tenues par le code :

1. Le jeton est tire au hasard sur 32 octets, jamais derive de l'identifiant du
   tableau. Un lien qui fuite ne compromet que ce tableau-la, et le regenerer
   revoque instantanement tous ceux qui circulaient.
2. La reponse ne porte ni l'espace, ni l'organisation, ni l'auteur. Le visiteur
   voit des chiffres et le SQL qui les produit, rien de la structure interne.
3. Aucune ecriture n'est possible, et le SQL repasse par le garde-fou a chaque
   affichage - exactement comme pour un membre authentifie.

Ce qui manque, et qui est ecrit ici pour que personne ne le decouvre en
production : cette route n'est pas limitee en debit. Le module `limiteur` existe
dans le depot mais n'est branche nulle part. Tant que ce n'est pas fait, un lien
partage peut etre sollicite sans frein, et chaque appel rejoue de vraies
requetes sur l'entrepot.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dashboard import AnalyseReponse, GraphiqueReponse, ResultatReponse
from app.schemas.partage import TableauPartageReponse, WidgetPartageReponse
from app.services.chat_service import extrait_json
from app.services.dashboard_service import DashboardService, WidgetVivant

router = APIRouter(prefix="/partage", tags=["partage"])


@router.get("/{jeton}", response_model=TableauPartageReponse)
async def consulter(jeton: str, db: AsyncSession = Depends(get_db)):
    """Le tableau designe par ce lien, requetes rejouees a l'instant."""
    service = DashboardService(db)
    dashboard, espace = await service.par_jeton(jeton)
    vivants = await service.rafraichir(espace, dashboard)
    return TableauPartageReponse(
        nom=dashboard.nom,
        widgets=[_widget(v) for v in vivants],
        rejoue_le=datetime.now(UTC),
    )


def _widget(vivant: WidgetVivant) -> WidgetPartageReponse:
    w = vivant.widget
    return WidgetPartageReponse(
        titre=w.titre,
        sql=w.sql,
        position=w.position,
        graphique=GraphiqueReponse(**w.graphique) if w.graphique else None,
        resultat=ResultatReponse(**extrait_json(vivant.resultat)) if vivant.resultat else None,
        analyse=AnalyseReponse(**vivant.analyse.en_dict()) if vivant.analyse else None,
        erreur=vivant.erreur,
    )
