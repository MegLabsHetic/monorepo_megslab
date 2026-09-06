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
from app.agents.viz import SpecGraphique
from app.core.duckdb_engine import ColonneProfil, ErreurRequete, Resultat, TableProfil
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import Consommation, Reponse
from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
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
        elif format_sortie is SpecGraphique:
            contenu = SpecGraphique(type="aucun", raison="test")
        else:
            raise AssertionError(f"format inattendu : {format_sortie}")
        return Reponse(contenu=contenu, consommation=CONSOMMATION)


class FauxMoteur:
    def __init__(self, schema: str) -> None:
        self.schema_demande = schema
        self.schema_entrepot = schema
        self.sql_execute: str | None = None

    def profil_complet(self):
        return [
            TableProfil(
                nom="ventes",
                nb_lignes=3,
                colonnes=(
                    ColonneProfil("id", "BIGINT", 0.0, 3, None),
                    ColonneProfil("montant", "DOUBLE", 0.0, 3, None),
                ),
            )
        ]

    def executer(self, sql: str, lignes_max: int = 5000) -> Resultat:
        self.sql_execute = sql
        return Resultat(colonnes=["n"], lignes=[(3,)], tronque=False)


async def _espace_et_utilisateur(db: AsyncSession) -> tuple[Workspace, User, Conversation]:
    organisation = Organization(nom="Acme")
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    db.add_all([organisation, utilisateur])
    await db.flush()
    espace = Workspace(
        organization_id=organisation.id,
        nom="General",
        airbyte_workspace_id="w",
        airbyte_destination_id="d",
        schema_entrepot=f"org_{organisation.id}",
    )
    db.add(espace)
    await db.flush()
    conversation = Conversation(workspace_id=espace.id, user_id=utilisateur.id)
    db.add(conversation)
    await db.flush()
    return espace, utilisateur, conversation


async def test_une_question_produit_une_reponse_du_sql_et_un_cout(db: AsyncSession) -> None:
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    llm = FauxLLM()
    moteurs: list[FauxMoteur] = []

    def fabrique(schema: str) -> FauxMoteur:
        moteur = FauxMoteur(schema)
        moteurs.append(moteur)
        return moteur

    question = await ChatService(db, llm, fabrique).poser(  # type: ignore[arg-type]
        espace, utilisateur, conversation, "Combien de ventes ?"
    )

    assert question.reponse == "Il y a 3 ventes."
    assert question.sql is not None and "SELECT" in question.sql
    assert question.resultat == {"colonnes": ["n"], "lignes": [[3]], "tronque": False}
    assert llm.appels == ["PlanRequete", "Redaction"]
    # Deux appels au modele, additionnes.
    assert question.jetons == 2 * CONSOMMATION.jetons_total
    assert question.cout_dollars == pytest.approx(2 * CONSOMMATION.cout_dollars)
    assert [e["agent"] for e in question.etapes] == ["data", "analyste", "ml", "redacteur", "viz"]
    # Une seule ligne : ni serie a analyser, ni graphique a demander.
    assert [e["statut"] for e in question.etapes] == [
        "terminee",
        "terminee",
        "ignoree",
        "terminee",
        "ignoree",
    ]
    assert question.analyse is None and question.graphique is None
    # Le schema demande au moteur est bien celui de l'organisation.
    assert moteurs[0].schema_demande == espace.schema_entrepot


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
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    llm = FauxLLMQuiCorrige()
    moteur = FauxMoteurCapricieux("x")

    question = await ChatService(db, llm, lambda _: moteur).poser(  # type: ignore[arg-type]
        espace, utilisateur, conversation, "Combien de ventes ?"
    )

    assert len(moteur.tentatives) == 2
    assert question.sql is not None and "TRY_CAST" in question.sql
    # Le modele a recu l'erreur exacte du moteur, pas la phrase destinee a l'utilisateur.
    assert "Binder Error" in llm.questions[1]
    assert llm.appels == ["PlanRequete", "PlanRequete", "Redaction"]
    # La reprise a coute un appel de plus, et le compte-rendu le dit.
    assert question.jetons == 3 * CONSOMMATION.jetons_total
    assert question.etapes[1]["detail"].endswith("apres une correction")


async def test_une_deuxieme_erreur_du_moteur_est_rendue_sans_insister(db: AsyncSession) -> None:
    """Une seule reprise : si la correction echoue aussi, on ne boucle pas."""
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    llm = FauxLLM()
    moteur = FauxMoteurCapricieux("x", echecs=2)

    with pytest.raises(ErreurUtilisateur) as capture:
        await ChatService(db, llm, lambda _: moteur).poser(  # type: ignore[arg-type]
            espace, utilisateur, conversation, "Combien de ventes ?"
        )

    assert capture.value.code_http == 422
    assert len(moteur.tentatives) == 2
    assert llm.appels == ["PlanRequete", "PlanRequete"]  # pas de Redacteur, pas de 3e essai


async def test_le_sql_du_modele_passe_par_le_garde_fou(db: AsyncSession) -> None:
    """Un DELETE propose par le modele ne doit jamais atteindre le moteur."""
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    llm = FauxLLM(sql='DELETE FROM entrepot."ventes"')
    moteur = FauxMoteur("x")

    with pytest.raises(ErreurUtilisateur) as capture:
        await ChatService(db, llm, lambda _: moteur).poser(  # type: ignore[arg-type]
            espace, utilisateur, conversation, "Supprime tout"
        )

    assert capture.value.code_http == 422
    assert moteur.sql_execute is None
    assert llm.appels == ["PlanRequete"]  # le Redacteur n'a pas ete appele


async def test_sans_table_dans_l_entrepot_on_refuse_avant_d_appeler_le_modele(
    db: AsyncSession,
) -> None:
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    llm = FauxLLM()

    class MoteurVide(FauxMoteur):
        def profil_complet(self):
            return []

    with pytest.raises(ErreurUtilisateur) as capture:
        await ChatService(db, llm, MoteurVide).poser(  # type: ignore[arg-type]
            espace, utilisateur, conversation, "Combien ?"
        )

    assert capture.value.code_http == 409
    assert llm.appels == []


async def test_l_historique_rend_les_questions_de_l_espace_seulement(db: AsyncSession) -> None:
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    autre = Workspace(
        organization_id=espace.organization_id,
        nom="Autre",
        airbyte_workspace_id="w2",
        airbyte_destination_id="d2",
        schema_entrepot="ws_autre",
    )
    db.add(autre)
    await db.flush()
    fil_autre = Conversation(workspace_id=autre.id, user_id=utilisateur.id)
    db.add(fil_autre)
    await db.flush()
    service = ChatService(db, FauxLLM(), FauxMoteur)  # type: ignore[arg-type]
    await service.poser(espace, utilisateur, conversation, "Question A")
    await service.poser(autre, utilisateur, fil_autre, "Question B")

    historique = await service.historique(espace)

    assert [q.texte for q in historique] == ["Question A"]


async def test_les_echanges_precedents_du_fil_sont_transmis_a_l_analyste(
    db: AsyncSession,
) -> None:
    """« Et par produit ? » n'a de sens qu'avec la question d'avant sous les yeux."""
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    llm = FauxLLMQuiCorrige()  # garde le texte de chaque demande
    service = ChatService(db, llm, FauxMoteur)  # type: ignore[arg-type]

    await service.poser(espace, utilisateur, conversation, "Combien de ventes ?")
    await service.poser(espace, utilisateur, conversation, "Et par produit ?")

    plans = [q for q, f in zip(llm.questions, llm.appels) if f == "PlanRequete"]
    assert plans[0] == "Combien de ventes ?"  # premiere question : rien avant
    assert "Combien de ventes ?" in plans[1] and "SELECT" in plans[1]
    assert plans[1].endswith("Nouvelle question : Et par produit ?")
    # Le fil prend pour titre sa premiere question.
    assert conversation.titre == "Combien de ventes ?"


async def test_chaque_etape_conserve_ce_qu_elle_a_coute(db: AsyncSession) -> None:
    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    service = ChatService(db, FauxLLM(), FauxMoteur)  # type: ignore[arg-type]

    question = await service.poser(espace, utilisateur, conversation, "Combien de ventes ?")

    couts = {e["agent"]: e["cout_dollars"] for e in question.etapes}
    assert couts["analyste"] == pytest.approx(CONSOMMATION.cout_dollars)
    assert couts["redacteur"] == pytest.approx(CONSOMMATION.cout_dollars)
    assert couts["data"] == 0 and couts["ml"] == 0
    assert question.jetons_entree == 200 and question.jetons_sortie == 100


async def test_un_budget_atteint_refuse_la_question_avant_tout_appel_au_modele(
    db: AsyncSession,
) -> None:
    from app.models.organization import Organization as Org

    espace, utilisateur, conversation = await _espace_et_utilisateur(db)
    organisation = await db.get(Org, espace.organization_id)
    assert organisation is not None
    organisation.budget_mensuel_dollars = 0.0001
    organisation.budget_bloquant = True
    await db.flush()
    llm = FauxLLM()
    service = ChatService(db, llm, FauxMoteur)  # type: ignore[arg-type]
    # Une premiere question passe : rien n'a encore ete depense.
    await service.poser(espace, utilisateur, conversation, "Combien de ventes ?")

    with pytest.raises(ErreurUtilisateur) as capture:
        await service.poser(espace, utilisateur, conversation, "Et par produit ?")

    assert capture.value.code_http == 402
    assert llm.appels == ["PlanRequete", "Redaction"]  # la deuxieme n'a rien appele
