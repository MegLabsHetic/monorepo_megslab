"""L'assistant enchaine Analyste et Redacteur, garde le SQL, et compte le cout.

Ni modele ni entrepot reels : un faux LLM rend des reponses preparees, un faux
moteur rend un schema et un resultat fixes. Ce qu'on verifie ici, c'est
l'assemblage — pas la qualite du SQL du modele.
"""

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyste import PlanRequete
from app.agents.redacteur import Redaction
from app.core.duckdb_engine import ErreurRequete, Resultat
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import Consommation, Reponse
from app.models.organization import Organization
from app.models.user import User
from app.services.chat_service import ChatService

CONSOMMATION = Consommation(
    jetons_entree=100, jetons_sortie=50, jetons_cache_lus=0, jetons_cache_ecrits=0
)


class FauxLLM:
    """Rend un plan pour l'Analyste et une redaction pour le Redacteur."""

    def __init__(self, sql: str = 'SELECT count(*) AS n FROM entrepot."ventes"') -> None:
        self.sql = sql
        self.appels: list[str] = []

    async def repondre(self, *, instructions, question, format_sortie: type[BaseModel], effort):
        self.appels.append(format_sortie.__name__)
        if format_sortie is PlanRequete:
            contenu = PlanRequete(sql=self.sql, tables_utilisees=["ventes"], explication="compte")
        elif format_sortie is Redaction:
            contenu = Redaction(reponse="Il y a 3 ventes.")
        else:
            raise AssertionError(f"format inattendu : {format_sortie}")
        return Reponse(contenu=contenu, consommation=CONSOMMATION)


class FauxMoteur:
    def __init__(self, schema: str) -> None:
        self.schema_demande = schema
        self.sql_execute: str | None = None

    def schema(self):
        return [("ventes", [("id", "BIGINT"), ("montant", "DOUBLE")])]

    def executer(self, sql: str, lignes_max: int = 5000) -> Resultat:
        self.sql_execute = sql
        return Resultat(colonnes=["n"], lignes=[(3,)], tronque=False)


async def _organisation_et_utilisateur(db: AsyncSession) -> tuple[Organization, User]:
    organisation = Organization(nom="Acme", airbyte_workspace_id="w", airbyte_destination_id="d")
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    db.add_all([organisation, utilisateur])
    await db.flush()
    return organisation, utilisateur


async def test_une_question_produit_une_reponse_du_sql_et_un_cout(db: AsyncSession) -> None:
    organisation, utilisateur = await _organisation_et_utilisateur(db)
    llm = FauxLLM()
    moteurs: list[FauxMoteur] = []

    def fabrique(schema: str) -> FauxMoteur:
        moteur = FauxMoteur(schema)
        moteurs.append(moteur)
        return moteur

    question = await ChatService(db, llm, fabrique).poser(  # type: ignore[arg-type]
        organisation, utilisateur, "Combien de ventes ?"
    )

    assert question.reponse == "Il y a 3 ventes."
    assert question.sql is not None and "SELECT" in question.sql
    assert question.resultat == {"colonnes": ["n"], "lignes": [[3]], "tronque": False}
    assert llm.appels == ["PlanRequete", "Redaction"]
    # Deux appels au modele, additionnes.
    assert question.jetons == 2 * CONSOMMATION.jetons_total
    assert question.cout_dollars == pytest.approx(2 * CONSOMMATION.cout_dollars)
    assert [e["agent"] for e in question.etapes] == ["analyste", "redacteur"]
    # Le schema demande au moteur est bien celui de l'organisation.
    assert moteurs[0].schema_demande == f"org_{organisation.id}"


class FauxMoteurCapricieux(FauxMoteur):
    """Rejette les premieres requetes, comme un moteur devant une date en VARCHAR."""

    def __init__(self, schema: str, echecs: int = 1) -> None:
        super().__init__(schema)
        self.echecs = echecs
        self.tentatives: list[str] = []

    def executer(self, sql: str, lignes_max: int = 5000) -> Resultat:
        self.tentatives.append(sql)
        if len(self.tentatives) <= self.echecs:
            raise ErreurRequete(
                "Cette requete n'a pas pu etre executee.",
                detail="Binder Error: No function matches date_diff(VARCHAR, VARCHAR)",
            )
        return super().executer(sql, lignes_max)


class FauxLLMQuiCorrige(FauxLLM):
    """Rend un SQL corrige quand on lui renvoie l'erreur du moteur."""

    def __init__(self) -> None:
        super().__init__()
        self.questions: list[str] = []

    async def repondre(self, *, instructions, question, format_sortie: type[BaseModel], effort):
        self.questions.append(question)
        if format_sortie is PlanRequete and "rejetee" in question:
            self.sql = (
                'SELECT count(*) AS n FROM entrepot."ventes" WHERE TRY_CAST(montant AS DOUBLE) > 0'
            )
        return await super().repondre(
            instructions=instructions, question=question, format_sortie=format_sortie, effort=effort
        )


async def test_une_requete_rejetee_par_le_moteur_est_corrigee_une_fois(db: AsyncSession) -> None:
    organisation, utilisateur = await _organisation_et_utilisateur(db)
    llm = FauxLLMQuiCorrige()
    moteur = FauxMoteurCapricieux("x")

    question = await ChatService(db, llm, lambda _: moteur).poser(  # type: ignore[arg-type]
        organisation, utilisateur, "Combien de ventes ?"
    )

    assert len(moteur.tentatives) == 2
    assert question.sql is not None and "TRY_CAST" in question.sql
    # Le modele a recu l'erreur exacte du moteur, pas la phrase destinee a l'utilisateur.
    assert "Binder Error" in llm.questions[1]
    assert llm.appels == ["PlanRequete", "PlanRequete", "Redaction"]
    # La reprise a coute un appel de plus, et le compte-rendu le dit.
    assert question.jetons == 3 * CONSOMMATION.jetons_total
    assert question.etapes[0]["detail"].endswith("apres une correction")


async def test_une_deuxieme_erreur_du_moteur_est_rendue_sans_insister(db: AsyncSession) -> None:
    """Une seule reprise : si la correction echoue aussi, on ne boucle pas."""
    organisation, utilisateur = await _organisation_et_utilisateur(db)
    llm = FauxLLM()
    moteur = FauxMoteurCapricieux("x", echecs=2)

    with pytest.raises(ErreurUtilisateur) as capture:
        await ChatService(db, llm, lambda _: moteur).poser(  # type: ignore[arg-type]
            organisation, utilisateur, "Combien de ventes ?"
        )

    assert capture.value.code_http == 422
    assert len(moteur.tentatives) == 2
    assert llm.appels == ["PlanRequete", "PlanRequete"]  # pas de Redacteur, pas de 3e essai


async def test_le_sql_du_modele_passe_par_le_garde_fou(db: AsyncSession) -> None:
    """Un DELETE propose par le modele ne doit jamais atteindre le moteur."""
    organisation, utilisateur = await _organisation_et_utilisateur(db)
    llm = FauxLLM(sql='DELETE FROM entrepot."ventes"')
    moteur = FauxMoteur("x")

    with pytest.raises(ErreurUtilisateur) as capture:
        await ChatService(db, llm, lambda _: moteur).poser(  # type: ignore[arg-type]
            organisation, utilisateur, "Supprime tout"
        )

    assert capture.value.code_http == 422
    assert moteur.sql_execute is None
    assert llm.appels == ["PlanRequete"]  # le Redacteur n'a pas ete appele


async def test_sans_table_dans_l_entrepot_on_refuse_avant_d_appeler_le_modele(
    db: AsyncSession,
) -> None:
    organisation, utilisateur = await _organisation_et_utilisateur(db)
    llm = FauxLLM()

    class MoteurVide(FauxMoteur):
        def schema(self):
            return []

    with pytest.raises(ErreurUtilisateur) as capture:
        await ChatService(db, llm, MoteurVide).poser(  # type: ignore[arg-type]
            organisation, utilisateur, "Combien ?"
        )

    assert capture.value.code_http == 409
    assert llm.appels == []


async def test_l_historique_rend_les_questions_de_l_organisation_seulement(
    db: AsyncSession,
) -> None:
    organisation, utilisateur = await _organisation_et_utilisateur(db)
    autre = Organization(nom="Autre", airbyte_workspace_id="w2", airbyte_destination_id="d2")
    db.add(autre)
    await db.flush()
    service = ChatService(db, FauxLLM(), FauxMoteur)  # type: ignore[arg-type]
    await service.poser(organisation, utilisateur, "Question A")
    await service.poser(autre, utilisateur, "Question B")

    historique = await service.historique(organisation)

    assert [q.texte for q in historique] == ["Question A"]
