"""L'agent ML ne parle que si le resultat est une serie, et dit ce qu'il a calcule."""

from datetime import date, timedelta

from app.agents.ml import MIN_POINTS, AgentML
from app.core.duckdb_engine import Resultat


def _serie(x: list, y: list, colonnes: tuple[str, str] = ("mois", "ventes")) -> Resultat:
    return Resultat(colonnes=list(colonnes), lignes=list(zip(x, y)), tronque=False)


def test_serie_mensuelle_en_hausse_avec_une_anomalie_et_une_projection() -> None:
    mois = [f"2024-{m:02d}" for m in range(1, 13)]
    ventes = [100.0 + 10 * i for i in range(12)]
    ventes[6] = 400.0  # une pointe en juillet

    analyse = AgentML().analyser(_serie(mois, ventes))

    assert analyse is not None
    assert (analyse.colonne_x, analyse.colonne_y) == ("mois", "ventes")
    assert analyse.tendance == "hausse"
    assert [a.x for a in analyse.anomalies] == ["2024-07"]
    assert [p.x for p in analyse.previsions] == ["2025-01", "2025-02", "2025-03"]
    premiere = analyse.previsions[0]
    assert premiere.y_min < premiere.y < premiere.y_max
    resume = analyse.resume()
    assert "hausse" in resume and "2024-07" in resume and "Projection lineaire" in resume


def test_des_premiers_du_mois_en_timestamp_sont_lus_comme_des_mois() -> None:
    """DATE_TRUNC('month') rend « 2017-01-01 00:00:00 » : la projection doit suivre les mois."""
    mois = [f"2017-{m:02d}-01 00:00:00" for m in range(1, 13)]
    ventes = [100.0 + 10 * i for i in range(12)]

    analyse = AgentML().analyser(_serie(mois, ventes))

    assert analyse is not None
    assert [p.x for p in analyse.previsions] == ["2018-01", "2018-02", "2018-03"]


def test_des_dates_reelles_donnent_un_pas_hebdomadaire() -> None:
    semaines = [date(2024, 1, 1) + timedelta(days=7 * i) for i in range(10)]
    montants = [50.0 + 2 * i for i in range(10)]

    analyse = AgentML().analyser(_serie(semaines, montants, ("semaine", "montant")))

    assert analyse is not None
    assert analyse.tendance == "hausse"
    assert analyse.anomalies == ()  # parfaitement lineaire : aucun ecart
    assert analyse.previsions[0].x == "2024-03-11"  # 2024-03-04 + 7 jours


def test_une_serie_plate_est_stable_et_se_projette_a_l_identique() -> None:
    annees = list(range(2015, 2025))

    analyse = AgentML().analyser(_serie(annees, [42.0] * 10, ("annee", "clients")))

    assert analyse is not None
    assert analyse.tendance == "stable"
    assert analyse.anomalies == ()
    assert [p.x for p in analyse.previsions] == ["2025", "2026", "2027"]
    assert analyse.previsions[0].y == 42.0


def test_du_bruit_sans_tendance_ne_se_projette_pas() -> None:
    mois = [f"2024-{m:02d}" for m in range(1, 13)]
    valeurs = [100.0, 300.0] * 6

    analyse = AgentML().analyser(_serie(mois, valeurs))

    assert analyse is not None
    assert analyse.tendance == "sans tendance nette"
    assert analyse.previsions == ()
    assert "ne suit pas de tendance" in analyse.resume()


def test_les_lignes_sont_triees_par_date_avant_la_regression() -> None:
    mois = [f"2024-{m:02d}" for m in range(12, 0, -1)]
    ventes = [100.0 + 10 * m for m in range(12, 0, -1)]

    analyse = AgentML().analyser(_serie(mois, ventes))

    assert analyse is not None
    assert analyse.tendance == "hausse"
    assert analyse.previsions[0].x == "2025-01"


def test_pas_de_serie_sans_axe_temporel() -> None:
    resultat = Resultat(
        colonnes=["etat", "commandes"],
        lignes=[(f"E{i}", 10.0 * i) for i in range(12)],
        tronque=False,
    )
    assert AgentML().analyser(resultat) is None


def test_trop_peu_de_points_pour_une_droite() -> None:
    mois = [f"2024-{m:02d}" for m in range(1, MIN_POINTS)]
    assert AgentML().analyser(_serie(mois, [1.0] * len(mois))) is None


def test_les_nuls_sont_ecartes_avant_de_compter_les_points() -> None:
    mois = [f"2024-{m:02d}" for m in range(1, 13)]
    ventes: list[float | None] = [100.0 + 10 * i for i in range(12)]
    ventes[3] = None

    analyse = AgentML().analyser(_serie(mois, ventes))

    assert analyse is not None
    assert analyse.nb_points == 11
