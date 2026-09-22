"""Ce que coute un millier de jetons, chez qui, et pour quel modele.

Les tarifs vivaient dans le client Anthropic sous forme de constantes. Des lors
qu'il existe plusieurs fournisseurs, un cout ne se calcule plus sans savoir qui
a repondu : le tarif accompagne donc la consommation, il n'est plus implicite.

ATTENTION : un tarif perime fausse le compteur qu'on montre a l'utilisateur.
Chaque entree porte la date de son releve. A reverifier avant toute
demonstration, et de toute facon avant de facturer quoi que ce soit.
"""

from dataclasses import dataclass

# Taux de conversion utilise pour les fournisseurs qui publient en euros.
# Approximatif et date : il sert a comparer des ordres de grandeur, pas a
# etablir une facture.
EURO_EN_DOLLARS = 1.08


@dataclass(frozen=True)
class Localisation:
    """Ou l'inference a lieu, et sous quel droit.

    Ce n'est pas une declaration d'editeur : pour OVHcloud, le point de
    terminaison a ete resolu et son adresse verifiee aupres du RIPE le
    9 septembre 2026 (AS16276 OVH SAS, Dunkerque). Voir l'annexe du memoire.
    """

    pays: str
    drapeau: str
    ville: str = ""
    dans_l_union_europeenne: bool = True
    verifiee: bool = False

    @property
    def libelle(self) -> str:
        return f"{self.ville}, {self.pays}" if self.ville else self.pays


LOCALISATIONS: dict[str, Localisation] = {
    "ovhcloud": Localisation("France", "🇫🇷", "Gravelines", True, verifiee=True),
    "scaleway": Localisation("France", "🇫🇷", "Paris", True),
    "ionos": Localisation("Allemagne", "🇩🇪", "", True),
    "anthropic": Localisation("États-Unis", "🇺🇸", "", dans_l_union_europeenne=False),
}

INCONNUE = Localisation("inconnue", "🏳", "", dans_l_union_europeenne=False)


@dataclass(frozen=True)
class Tarif:
    """Le prix d'un modele chez un fournisseur, en dollars par million de jetons."""

    fournisseur: str
    modele: str
    entree: float
    sortie: float
    # Seul Anthropic facture la mise en cache a ce jour. Zero ailleurs : les
    # fournisseurs europeens testes ne proposent pas de cache d'instructions.
    cache_lecture: float = 0.0
    cache_ecriture: float = 0.0

    @property
    def libelle(self) -> str:
        return f"{self.fournisseur}/{self.modele}"

    @property
    def localisation(self) -> Localisation:
        return LOCALISATIONS.get(self.fournisseur, INCONNUE)


def _euros(montant: float) -> float:
    return round(montant * EURO_EN_DOLLARS, 6)


# Releve du 6 septembre 2026, documentation de l'API Anthropic.
ANTHROPIC_OPUS_5 = Tarif(
    fournisseur="anthropic",
    modele="claude-opus-5",
    entree=5.00,
    sortie=25.00,
    cache_lecture=0.50,
    cache_ecriture=6.25,
)

# Releve du 9 septembre 2026 sur l'API du service elle-meme :
#   GET https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/models
OVH_GPT_OSS_120B = Tarif("ovhcloud", "gpt-oss-120b", entree=0.090, sortie=0.470)
OVH_GPT_OSS_20B = Tarif("ovhcloud", "gpt-oss-20b", entree=0.050, sortie=0.180)
OVH_QWEN3_CODER_30B = Tarif("ovhcloud", "Qwen3-Coder-30B-A3B-Instruct", entree=0.070, sortie=0.260)
OVH_QWEN35_397B = Tarif("ovhcloud", "Qwen3.5-397B-A17B", entree=0.710, sortie=4.250)

# Releve du 9 septembre 2026, grilles publiees en euros, converties ci-dessus.
SCALEWAY_GPT_OSS_120B = Tarif("scaleway", "gpt-oss-120b", entree=_euros(0.15), sortie=_euros(0.60))
SCALEWAY_QWEN35_397B = Tarif(
    "scaleway", "Qwen3.5-397B-A17B", entree=_euros(0.60), sortie=_euros(3.60)
)
IONOS_GPT_OSS_120B = Tarif("ionos", "gpt-oss-120b", entree=_euros(0.15), sortie=_euros(0.65))
IONOS_QWEN35_397B = Tarif("ionos", "Qwen3.5-397B-A17B", entree=_euros(0.60), sortie=_euros(3.60))


CATALOGUE: dict[tuple[str, str], Tarif] = {
    (t.fournisseur, t.modele): t
    for t in (
        ANTHROPIC_OPUS_5,
        OVH_GPT_OSS_120B,
        OVH_GPT_OSS_20B,
        OVH_QWEN3_CODER_30B,
        OVH_QWEN35_397B,
        SCALEWAY_GPT_OSS_120B,
        SCALEWAY_QWEN35_397B,
        IONOS_GPT_OSS_120B,
        IONOS_QWEN35_397B,
    )
}


class TarifInconnu(RuntimeError):
    """On refuse d'appeler un modele dont on ne sait pas facturer l'usage.

    Compter le cout est une promesse faite a l'utilisateur : un modele sans
    tarif connu produirait un cout affiche a zero, c'est-a-dire un mensonge.
    """


def tarif_de(fournisseur: str, modele: str) -> Tarif:
    tarif = CATALOGUE.get((fournisseur, modele))
    if tarif is None:
        raise TarifInconnu(
            f"Aucun tarif connu pour {fournisseur}/{modele}. "
            "Ajoutez-le dans app/core/tarifs.py avant de l'utiliser."
        )
    return tarif
