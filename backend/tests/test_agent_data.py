"""L'agent Data decrit l'entrepot sans modele, et ne le relit que quand il le faut."""

from app.agents.data import DUREE_CACHE_SECONDES, AgentData
from app.core.duckdb_engine import ColonneProfil, TableProfil


class MoteurProfil:
    def __init__(self, schema: str = "org_test") -> None:
        self.schema_entrepot = schema
        self.appels = 0

    def profil_complet(self) -> list[TableProfil]:
        self.appels += 1
        return [
            TableProfil(
                nom="orders",
                nb_lignes=99_441,
                colonnes=(
                    ColonneProfil("order_id", "VARCHAR", 0.0, 99_441, None),
                    ColonneProfil(
                        "order_status", "VARCHAR", 0.0, 3, ("canceled", "delivered", "shipped")
                    ),
                    ColonneProfil("order_delivered_customer_date", "VARCHAR", 3.0, 95_000, None),
                    ColonneProfil("freight", "DOUBLE", 12.5, 5_000, None),
                ),
            )
        ]


class Horloge:
    def __init__(self) -> None:
        self.t = 1_000.0

    def __call__(self) -> float:
        return self.t


def test_le_texte_donne_types_effectifs_modalites_et_vides() -> None:
    contexte = AgentData(MoteurProfil()).decrire()

    texte = contexte.texte()
    assert 'entrepot."orders" (99 441 lignes)' in texte
    assert "order_status VARCHAR — modalites : canceled, delivered, shipped" in texte
    assert "freight DOUBLE — 12 % de vides" in texte
    # 3 % de vides : sous le seuil, rien n'est ajoute.
    assert "order_delivered_customer_date VARCHAR\n" in texte
    assert contexte.resume() == "1 table(s), 4 colonne(s), 99 441 ligne(s)"
    assert not contexte.depuis_cache


def test_le_profil_est_garde_en_memoire_puis_relu_apres_expiration() -> None:
    moteur, horloge = MoteurProfil(), Horloge()
    agent = AgentData(moteur, horloge)

    premier = agent.decrire()
    second = agent.decrire()
    assert moteur.appels == 1
    assert not premier.depuis_cache and second.depuis_cache

    horloge.t += DUREE_CACHE_SECONDES + 1
    troisieme = agent.decrire()
    assert moteur.appels == 2
    assert not troisieme.depuis_cache


def test_oublier_force_une_relecture() -> None:
    moteur = MoteurProfil()
    agent = AgentData(moteur)

    agent.decrire()
    AgentData.oublier("org_test")
    agent.decrire()

    assert moteur.appels == 2


def test_deux_organisations_ne_partagent_pas_leur_contexte() -> None:
    a, b = MoteurProfil("org_a"), MoteurProfil("org_b")

    AgentData(a).decrire()
    AgentData(b).decrire()
    AgentData(a).decrire()

    assert (a.appels, b.appels) == (1, 1)


def test_un_entrepot_vide_se_reconnait() -> None:
    class Vide(MoteurProfil):
        def profil_complet(self) -> list[TableProfil]:
            return []

    contexte = AgentData(Vide()).decrire()
    assert contexte.est_vide
    assert contexte.texte() == ""
