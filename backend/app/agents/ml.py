"""L'agent ML : lit un resultat comme une serie et en tire ce que la statistique permet.

Pas de modele de langage ici : une regression lineaire, des residus, un seuil.
Ce qu'il produit est calcule, reproductible, et dit ce qu'il est — une
projection lineaire, pas une prophetie. Le Redacteur le cite, il ne le
complete pas.

L'agent se tait quand le resultat n'est pas une serie : pas d'axe ordonne,
pas de colonne numerique, ou trop peu de points pour qu'une droite veuille
dire quelque chose.
"""

import math
import statistics
from dataclasses import asdict, dataclass
from datetime import date, datetime

from app.agents.valeurs import est_annee, est_date, genre_colonne
from app.core.duckdb_engine import Resultat

MIN_POINTS = 8
MAX_POINTS = 5_000
# Un residu a plus de 2,5 ecarts-types de la droite : moins d'un point sur
# cent y arrive par hasard sur une serie a peu pres reguliere.
SEUIL_ANOMALIE = 2.5
ANOMALIES_MAX = 5
HORIZON = 3
# En dessous de ce R², la droite n'explique pas la serie : on ne parle pas de
# tendance, et on ne projette pas.
SEUIL_TENDANCE_R2 = 0.2
SEUIL_STABLE_PCT = 5.0
# Demi-largeur de l'intervalle a 95 % pour des residus a peu pres gaussiens.
FACTEUR_INTERVALLE = 1.96


@dataclass(frozen=True)
class Anomalie:
    x: str
    y: float
    ecart: float  # en ecarts-types des residus


@dataclass(frozen=True)
class Prevision:
    x: str
    y: float
    y_min: float
    y_max: float


@dataclass(frozen=True)
class AnalyseSerie:
    colonne_x: str
    colonne_y: str
    nb_points: int
    pente: float
    variation_pct: float | None
    r2: float
    tendance: str  # "hausse" | "baisse" | "stable" | "sans tendance nette"
    anomalies: tuple[Anomalie, ...]
    previsions: tuple[Prevision, ...]

    def en_dict(self) -> dict:
        return asdict(self)

    def resume(self) -> str:
        """Ce que le Redacteur recoit : des faits calcules, formules sobrement."""
        phrases = [self._phrase_tendance()]
        if self.anomalies:
            points = ", ".join(f"{a.x} ({_nombre(a.y)})" for a in self.anomalies)
            phrases.append(
                f"{len(self.anomalies)} point(s) s'ecartent nettement de la droite : {points}."
            )
        if self.previsions:
            projection = ", ".join(f"{p.x} ≈ {_nombre(p.y)}" for p in self.previsions)
            phrases.append(
                f"Projection lineaire des {len(self.previsions)} periodes suivantes "
                f"(a prendre comme un ordre de grandeur) : {projection}."
            )
        return " ".join(phrases)

    def _phrase_tendance(self) -> str:
        debut = f"Sur {self.nb_points} points ({self.colonne_x}), {self.colonne_y}"
        if self.tendance == "sans tendance nette":
            return f"{debut} ne suit pas de tendance lineaire nette (R² {self.r2:.2f})."
        variation = (
            f" : {self.variation_pct:+.0f} % entre le debut et la fin de la droite ajustee"
            if self.variation_pct is not None
            else ""
        )
        return f"{debut} est en {self.tendance}{variation} (R² {self.r2:.2f})."


class AgentML:
    def analyser(self, resultat: Resultat) -> AnalyseSerie | None:
        serie = _extraire_serie(resultat)
        if serie is None:
            return None
        colonne_x, colonne_y, axe, points = serie

        t = list(range(len(points)))
        y = [valeur for _, valeur in points]
        pente, ordonnee = _regression(t, y)
        residus = [yi - (ordonnee + pente * ti) for ti, yi in zip(t, y)]
        r2 = _r2(y, residus)
        ecart_type = _ecart_type(residus)

        anomalies = _anomalies(points, residus, ecart_type)
        tendance, variation = _tendance(pente, ordonnee, len(points), r2)
        previsions = (
            _previsions(axe, len(points), pente, ordonnee, ecart_type)
            if tendance != "sans tendance nette"
            else ()
        )
        return AnalyseSerie(
            colonne_x=colonne_x,
            colonne_y=colonne_y,
            nb_points=len(points),
            pente=pente,
            variation_pct=variation,
            r2=r2,
            tendance=tendance,
            anomalies=anomalies,
            previsions=previsions,
        )


# --- Lecture de la serie ------------------------------------------------------


class _Axe:
    """Comment ordonner les x, et comment nommer ceux qu'on projette."""

    def __init__(self, genre: str, cles: list[float]) -> None:
        self.genre = genre
        self.cles = cles
        ecarts = [b - a for a, b in zip(cles, cles[1:])]
        pas = statistics.median(ecarts) if ecarts else 1.0
        self.pas = pas if pas > 0 else 1.0

    def libelle_suivant(self, k: int) -> str:
        cle = self.cles[-1] + k * self.pas
        if self.genre == "mois":
            annee, mois = divmod(int(round(cle)), 12)
            return f"{annee:04d}-{mois + 1:02d}"
        if self.genre == "date":
            return date.fromordinal(int(round(cle))).isoformat()
        if self.genre == "annee":
            return str(int(round(cle)))
        return _nombre(cle)


def _extraire_serie(resultat: Resultat) -> tuple[str, str, _Axe, list[tuple[str, float]]] | None:
    if not (MIN_POINTS <= resultat.nb_lignes <= MAX_POINTS):
        return None
    colonnes = list(zip(*resultat.lignes)) if resultat.lignes else []
    genres = [genre_colonne(list(valeurs)) for valeurs in colonnes]

    index_x = _choisir_x(colonnes, genres)
    if index_x is None:
        return None
    index_y = next(
        (i for i, genre in enumerate(genres) if genre == "nombre" and i != index_x), None
    )
    if index_y is None:
        return None

    points = [
        (ligne[index_x], float(ligne[index_y]))
        for ligne in resultat.lignes
        if ligne[index_x] is not None and ligne[index_y] is not None
    ]
    if len(points) < MIN_POINTS:
        return None

    genre_axe = _genre_axe(points[0][0])
    cles = [_cle(valeur, genre_axe) for valeur, _ in points]
    if genre_axe == "date" and _est_mensuel(cles):
        # DATE_TRUNC('month') rend des premiers du mois : une serie mensuelle,
        # pas quotidienne. Sans ca, la projection derive d'un jour par mois.
        genre_axe, cles = "mois", [_cle_mois(cle) for cle in cles]
    ordre = sorted(range(len(points)), key=lambda i: cles[i])
    axe = _Axe(genre_axe, [cles[i] for i in ordre])
    tries = [(str(points[i][0]), points[i][1]) for i in ordre]
    return resultat.colonnes[index_x], resultat.colonnes[index_y], axe, tries


def _choisir_x(colonnes: list[tuple], genres: list[str]) -> int | None:
    """L'axe : une date de preference, sinon une annee ; jamais un nombre quelconque."""
    for i, genre in enumerate(genres):
        if genre == "date":
            return i
    for i, valeurs in enumerate(colonnes):
        presentes = [v for v in valeurs if v is not None]
        if presentes and all(est_annee(v) for v in presentes):
            return i
    return None


def _genre_axe(valeur: object) -> str:
    if isinstance(valeur, (date, datetime)):
        return "date"
    if isinstance(valeur, str) and est_date(valeur):
        return "mois" if len(valeur) == 7 else "date"
    return "annee"


def _est_mensuel(cles_jours: list[float]) -> bool:
    """Des dates toutes au premier du mois, espacees d'environ un mois."""
    dates = sorted(date.fromordinal(int(cle)) for cle in cles_jours)
    if len(dates) < 2 or any(d.day != 1 for d in dates):
        return False
    ecarts = [(b - a).days for a, b in zip(dates, dates[1:])]
    return 28 <= statistics.median(ecarts) <= 31


def _cle_mois(cle_jour: float) -> float:
    d = date.fromordinal(int(cle_jour))
    return d.year * 12 + d.month - 1


def _cle(valeur: object, genre: str) -> float:
    if genre == "mois":
        annee, mois = str(valeur).split("-")
        return int(annee) * 12 + int(mois) - 1
    if genre == "date":
        if isinstance(valeur, datetime):
            return float(valeur.date().toordinal())
        if isinstance(valeur, date):
            return float(valeur.toordinal())
        return float(date.fromisoformat(str(valeur)[:10]).toordinal())
    return float(int(str(valeur)))


# --- Statistique --------------------------------------------------------------


def _regression(t: list[int], y: list[float]) -> tuple[float, float]:
    """Moindres carres : pente et ordonnee a l'origine."""
    n = len(t)
    moyenne_t, moyenne_y = sum(t) / n, sum(y) / n
    covariance = sum((ti - moyenne_t) * (yi - moyenne_y) for ti, yi in zip(t, y))
    variance_t = sum((ti - moyenne_t) ** 2 for ti in t)
    pente = covariance / variance_t if variance_t else 0.0
    return pente, moyenne_y - pente * moyenne_t


def _r2(y: list[float], residus: list[float]) -> float:
    moyenne = sum(y) / len(y)
    total = sum((yi - moyenne) ** 2 for yi in y)
    if total == 0:
        # Une serie plate : la droite l'explique entierement.
        return 1.0
    return max(0.0, 1 - sum(r * r for r in residus) / total)


def _ecart_type(residus: list[float]) -> float:
    if len(residus) < 3:
        return 0.0
    return math.sqrt(sum(r * r for r in residus) / (len(residus) - 2))


def _anomalies(
    points: list[tuple[str, float]], residus: list[float], ecart_type: float
) -> tuple[Anomalie, ...]:
    if ecart_type == 0:
        return ()
    candidats = [
        Anomalie(x=x, y=y, ecart=round(r / ecart_type, 2))
        for (x, y), r in zip(points, residus)
        if abs(r / ecart_type) >= SEUIL_ANOMALIE
    ]
    candidats.sort(key=lambda a: abs(a.ecart), reverse=True)
    return tuple(candidats[:ANOMALIES_MAX])


def _tendance(pente: float, ordonnee: float, n: int, r2: float) -> tuple[str, float | None]:
    debut, fin = ordonnee, ordonnee + pente * (n - 1)
    variation = (fin - debut) / abs(debut) * 100 if abs(debut) > 1e-9 else None
    if r2 < SEUIL_TENDANCE_R2:
        return "sans tendance nette", variation
    if variation is not None and abs(variation) < SEUIL_STABLE_PCT:
        return "stable", variation
    return ("hausse" if pente > 0 else "baisse"), variation


def _previsions(
    axe: _Axe, n: int, pente: float, ordonnee: float, ecart_type: float
) -> tuple[Prevision, ...]:
    marge = FACTEUR_INTERVALLE * ecart_type
    return tuple(
        Prevision(
            x=axe.libelle_suivant(k),
            y=round(ordonnee + pente * (n - 1 + k), 2),
            y_min=round(ordonnee + pente * (n - 1 + k) - marge, 2),
            y_max=round(ordonnee + pente * (n - 1 + k) + marge, 2),
        )
        for k in range(1, HORIZON + 1)
    )


def _nombre(valeur: float) -> str:
    if float(valeur).is_integer():
        return f"{int(valeur):,}".replace(",", " ")
    return f"{valeur:,.2f}".replace(",", " ")
