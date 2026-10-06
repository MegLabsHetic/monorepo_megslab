"""Classe chaque ecart du banc selon ce qui differe : le chiffre, ou son libelle.

Un verdict « faux » ne dit pas ce qui a echoue. Deux requetes peuvent rendre
exactement les memes montants sous des etiquettes differentes - « beleza_saude »
contre « health_beauty », « 2017-01 » contre « 2017 » - et le banc les separe
alors que l'utilisateur lirait le meme chiffre.

Le classement est MECANIQUE et verifiable : il compare le multi-ensemble des
valeurs numeriques rendues de part et d'autre, sans jamais interpreter le sens
de la question. Aucun jugement n'entre ici ; ce qui resiste au test est renvoye
a une lecture humaine plutot que range d'office du bon cote.

    python evaluation/classer_ecarts.py <ecarts.json> [sortie.json]
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Meme tolerance que le banc : deux calculs justes peuvent differer au centieme
# selon l'ordre des operations en virgule flottante.
DECIMALES = 2
# Au-dela, ce n'est plus un arrondi mais un calcul different. Un ecart relatif
# de un pour mille absorbe les conversions de type sans absoudre un filtre.
TOLERANCE_RELATIVE = 0.001

_NOMBRE = re.compile(r"^-?\d+(?:\.\d+)?$")


def nombres(lignes: list) -> Counter:
    """Le multi-ensemble des valeurs numeriques rendues, etiquettes ecartees."""
    valeurs: Counter = Counter()
    for ligne in lignes:
        for cellule in ligne:
            if _NOMBRE.fullmatch(str(cellule).strip()):
                valeurs[round(float(cellule), DECIMALES)] += 1
    return valeurs


def libelles(lignes: list) -> Counter:
    valeurs: Counter = Counter()
    for ligne in lignes:
        for cellule in ligne:
            texte = str(cellule).strip()
            if not _NOMBRE.fullmatch(texte):
                valeurs[texte] += 1
    return valeurs


def _contient(grand: Counter, petit: Counter) -> bool:
    return all(grand[valeur] >= combien for valeur, combien in petit.items())


def _proches(a: Counter, b: Counter) -> bool:
    """Les memes nombres a un pour mille pres, apparies du plus grand au plus petit.

    Les gros montants dominent l'appariement : c'est voulu, ce sont eux que la
    question demande, et un ecart d'arrondi sur un petit compte ne doit pas
    faire echouer la comparaison d'un chiffre d'affaires.
    """
    gauche = sorted(a.elements(), reverse=True)
    droite = sorted(b.elements(), reverse=True)
    if len(gauche) != len(droite):
        return False
    for x, y in zip(gauche, droite):
        ecart = abs(x - y)
        if ecart > max(abs(x), abs(y), 1.0) * TOLERANCE_RELATIVE:
            return False
    return True


def classer(dossier: dict) -> tuple[str, str]:
    """Rend la categorie de l'ecart et la preuve qui la fonde."""
    if dossier["impossible"]:
        return "refus", "question impossible : verdict deja pose par le banc"
    if dossier["produit_erreur"]:
        quoi = "garde-fou" if dossier["produit_erreur"].startswith("garde-fou") else "moteur"
        return "outil", f"{quoi} : {dossier['produit_erreur'][:150]}"
    if not dossier["sql_produit"]:
        return "refus", "aucun SQL produit sur une question repondable"

    ref, prod = dossier["reference_lignes"], dossier["produit_lignes"]
    # Le dossier ne conserve que douze lignes pour rester lisible, mais porte le
    # multi-ensemble numerique du resultat ENTIER : c'est lui qu'on compare, sans
    # quoi le test serait tronque d'un cote et pas de l'autre.
    nref = Counter({float(v): n for v, n in dossier["reference_nombres"].items()})
    nprod = Counter({float(v): n for v, n in dossier["produit_nombres"].items()})
    if not nref:
        return "a_lire", "la reference ne rend aucune valeur numerique"

    memes_lignes = dossier["reference_nb_lignes"] == dossier["produit_nb_lignes"]
    if memes_lignes and _contient(nprod, nref):
        manquants = sorted(set(libelles(ref)) - set(libelles(prod)))
        preuve = f"les {sum(nref.values())} valeurs de la reference sont rendues a l'identique"
        if manquants:
            preuve += f" ; libelles differents, par exemple « {manquants[0]} »"
        return "libelle", preuve
    if memes_lignes and _proches(nref, nprod):
        return "libelle", (
            f"memes {sum(nref.values())} valeurs a {TOLERANCE_RELATIVE:.1%} pres "
            "(arrondi ou type different)"
        )
    if _contient(nprod, nref):
        return "libelle", (
            f"les {sum(nref.values())} valeurs de la reference sont toutes rendues, "
            f"parmi {dossier['produit_nb_lignes']} lignes contre {dossier['reference_nb_lignes']}"
        )

    communs = sum((nref & nprod).values())
    return "a_lire", (
        f"{communs} valeur(s) commune(s) sur {sum(nref.values())} attendues : "
        "le chiffre differe, la cause demande une lecture"
    )


def principal(entree: Path, sortie: Path | None) -> None:
    dossiers = json.loads(entree.read_text(encoding="utf-8"))
    for dossier in dossiers:
        dossier["categorie"], dossier["preuve"] = classer(dossier)

    par_modele: dict[str, Counter] = {}
    for dossier in dossiers:
        par_modele.setdefault(dossier["modele"], Counter())[dossier["categorie"]] += 1

    for modele, comptes in par_modele.items():
        print(f"\n{modele} : {sum(comptes.values())} ecarts")
        for categorie, combien in comptes.most_common():
            print(f"  {categorie:.<28} {combien}")
        for dossier in dossiers:
            if dossier["modele"] != modele:
                continue
            print(f"    [{dossier['categorie']:8}] {dossier['question'][:62]}")
            print(f"               {dossier['preuve'][:110]}")

    if sortie:
        sortie.write_text(json.dumps(dossiers, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nEcrit : {sortie}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    principal(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
