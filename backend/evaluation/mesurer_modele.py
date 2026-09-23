"""Mesure la justesse d'un modele sur le jeu d'evaluation, par comparaison de resultats.

Le principe : on compare ce que la requete RENVOIE, pas son texte. Deux requetes
ecrites differemment qui rendent les memes lignes sont toutes deux justes, et
c'est le seul critere qui a du sens. Comparer le SQL mot a mot condamnerait
toute formulation qui n'est pas la notre.

Le chemin mesure est celui du produit : memes instructions que l'agent Analyste,
meme schema, meme garde-fou, meme moteur. Ce n'est donc pas la performance brute
d'un modele qu'on releve, c'est ce que l'utilisateur obtiendrait.

    OVHCLOUD_API_KEY=... python evaluation/mesurer_modele.py ovhcloud gpt-oss-120b

Le resultat est ecrit dans evaluation/mesure-<date>-<fournisseur>-<modele>.json,
avec pour chaque question le SQL produit, le verdict et sa raison.
"""

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.analyste import INSTRUCTIONS, PlanRequete  # noqa: E402
from app.agents.data import AgentData  # noqa: E402
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete  # noqa: E402
from app.core.errors import ErreurUtilisateur, FournisseurIndisponible  # noqa: E402
from app.core.fournisseur_openai import FournisseurOpenAICompatible  # noqa: E402
from app.core.sql_guard import SqlRefuse, valider  # noqa: E402

SCHEMA = "demo_olist"
JEU = Path(__file__).parent / "jeu-etendu.json"
# Les references sont identiques pour tous les modeles : les rejouer a chaque
# mesure ferait douze fois le meme travail sur l'entrepot. On les calcule une
# fois et on garde le resultat.
CACHE_REFERENCES = Path(__file__).parent / ".cache-references.json"

# Questions traitees de front. Le fournisseur autorise 400 requetes par minute ;
# la limite reelle est l'entrepot, atteint par un tunnel unique.
SIMULTANEES = 6

# Arrondi applique avant comparaison. Deux requetes justes peuvent differer au
# centieme selon l'ordre des operations en virgule flottante.
DECIMALES = 2


def normaliser(lignes) -> list:
    """Rend deux resultats comparables : valeurs arrondies, lignes triees.

    L'ordre des lignes n'est pas normalise quand la question demande un
    classement - mais on ne sait pas le deviner ici, donc on trie toujours et
    on l'assume : une erreur d'ordre sur un top-N passera pour juste. C'est une
    indulgence, et elle est declaree.
    """
    propres = []
    for ligne in lignes:
        cellules = []
        for valeur in ligne:
            if isinstance(valeur, bool):
                cellules.append(str(valeur))
            elif isinstance(valeur, (int, float)):
                cellules.append(f"{round(float(valeur), DECIMALES):.{DECIMALES}f}")
            else:
                cellules.append(str(valeur).strip())
        propres.append(cellules)
    return sorted(propres)


def comparer(produit, reference) -> tuple[bool, str]:
    a, b = normaliser(produit.lignes), normaliser(reference.lignes)
    if a == b:
        return True, "identique"
    if len(a) != len(b):
        return False, f"{len(a)} ligne(s) contre {len(b)} attendue(s)"
    differentes = sum(1 for x, y in zip(a, b) if x != y)
    return False, f"{differentes} ligne(s) differente(s) sur {len(b)}"


def charger_les_references(moteur, entrees) -> dict[str, list]:
    """Execute chaque reference une fois, et garde son resultat sur disque."""
    if CACHE_REFERENCES.exists():
        cache = json.loads(CACHE_REFERENCES.read_text(encoding="utf-8"))
        print(f"references en cache : {len(cache)}", flush=True)
        return cache
    cache = {}
    for rang, entree in enumerate(entrees, 1):
        if entree["sql_reference"] == "IMPOSSIBLE":
            continue
        resultat = moteur.executer(valider(entree["sql_reference"]))
        cache[entree["question"]] = normaliser(resultat.lignes)
        if rang % 20 == 0:
            print(f"  references : {len(cache)}", flush=True)
    CACHE_REFERENCES.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"references calculees : {len(cache)}", flush=True)
    return cache


async def mesurer(fournisseur: str, modele: str) -> dict:
    cle = os.environ.get(f"{fournisseur.upper()}_API_KEY", "")
    if not cle:
        print(f"Aucune cle dans {fournisseur.upper()}_API_KEY.", file=sys.stderr)
        sys.exit(1)

    moteur = DuckDBEngine(SCHEMA)
    schema_texte = AgentData(moteur).decrire().texte()
    llm = FournisseurOpenAICompatible(nom=fournisseur, modele=modele, cle_api=cle)
    entrees = json.load(open(JEU, encoding="utf-8"))
    references = charger_les_references(moteur, entrees)

    verrou = asyncio.Semaphore(SIMULTANEES)
    faits = [0]

    async def traiter(rang, entree):
        async with verrou:
            ligne = await _une_question(llm, moteur, schema_texte, entree, references)
        faits[0] += 1
        print(
            f"{faits[0]:3}/{len(entrees)}  {ligne['verdict']:18} "
            f"{ligne['raison'][:30]:32} {entree['question'][:40]}",
            flush=True,
        )
        return rang, ligne

    paires = await asyncio.gather(*(traiter(i, e) for i, e in enumerate(entrees)))
    resultats = [ligne for _, ligne in sorted(paires, key=lambda x: x[0])]
    return _synthese(fournisseur, modele, resultats, sum(r["cout"] for r in resultats))


async def _une_question(llm, moteur, schema_texte, entree, references) -> dict:
    attendu_impossible = entree["sql_reference"] == "IMPOSSIBLE"
    base = {
        "question": entree["question"],
        "famille": entree["famille"],
        "niveau": entree["niveau"],
        "impossible": attendu_impossible,
        "sql_produit": "",
        "cout": 0.0,
        "verdict": "",
        "raison": "",
    }

    try:
        reponse = await llm.repondre(
            instructions=INSTRUCTIONS,
            question=f"Schema :\n{schema_texte}\n\nQuestion : {entree['question']}",
            format_sortie=PlanRequete,
        )
    except (FournisseurIndisponible, ErreurUtilisateur) as erreur:
        return {**base, "verdict": "panne", "raison": str(erreur)[:120]}

    base["cout"] = reponse.consommation.cout_dollars
    base["sql_produit"] = reponse.contenu.sql.strip()

    # Le refus : l'Analyste laisse `sql` vide quand le schema ne permet pas.
    if not base["sql_produit"]:
        if attendu_impossible:
            return {**base, "verdict": "refus_correct", "raison": "refus attendu"}
        return {**base, "verdict": "refus_a_tort", "raison": reponse.contenu.explication[:120]}
    if attendu_impossible:
        return {**base, "verdict": "aurait_du_refuser", "raison": "a produit du SQL"}

    try:
        sql = valider(base["sql_produit"])
    except SqlRefuse as refus:
        return {**base, "verdict": "refuse_garde_fou", "raison": refus.raison[:120]}

    try:
        produit = await asyncio.to_thread(moteur.executer, sql)
    except ErreurRequete as erreur:
        return {**base, "verdict": "erreur_moteur", "raison": erreur.raison[:120]}

    attendu = references.get(entree["question"])
    if attendu is None:
        return {**base, "verdict": "reference_absente", "raison": "pas de resultat en cache"}

    obtenu = normaliser(produit.lignes)
    if obtenu == attendu:
        return {**base, "verdict": "juste", "raison": "identique"}
    if len(obtenu) != len(attendu):
        raison = f"{len(obtenu)} ligne(s) contre {len(attendu)}"
    else:
        raison = f"{sum(1 for x, y in zip(obtenu, attendu) if x != y)} ligne(s) differente(s)"
    return {**base, "verdict": "faux", "raison": raison}


def _synthese(fournisseur: str, modele: str, resultats: list, cout: float) -> dict:
    def combien(*verdicts):
        return sum(1 for r in resultats if r["verdict"] in verdicts)

    possibles = [r for r in resultats if not r["impossible"]]
    impossibles = [r for r in resultats if r["impossible"]]
    justes = combien("juste")
    refus_ok = sum(1 for r in impossibles if r["verdict"] == "refus_correct")

    synthese = {
        "fournisseur": fournisseur,
        "modele": modele,
        "date": date.today().isoformat(),
        "questions": len(resultats),
        "questions_possibles": len(possibles),
        "justes": justes,
        "questions_impossibles": len(impossibles),
        "refus_corrects": refus_ok,
        "cout_total_dollars": round(cout, 4),
        "cout_par_question": round(cout / max(1, len(resultats)), 5),
        "detail": resultats,
    }
    chemin = Path(__file__).parent / f"mesure-{synthese['date']}-{fournisseur}-{modele}.json"
    chemin.write_text(json.dumps(synthese, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"  {fournisseur}/{modele}")
    print(f"  Justes ............... {justes}/{len(possibles)}")
    print(f"  Refus corrects ....... {refus_ok}/{len(impossibles)}")
    for verdict in (
        "faux",
        "erreur_moteur",
        "refuse_garde_fou",
        "refus_a_tort",
        "aurait_du_refuser",
        "panne",
        "reference_cassee",
    ):
        n = combien(verdict)
        if n:
            print(f"  {verdict:.<21} {n}")
    print(f"  Cout total ........... {cout:.4f} $")
    print(f"  Ecrit : {chemin.name}")
    print("=" * 70)
    return synthese


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    asyncio.run(mesurer(sys.argv[1], sys.argv[2]))
