"""Rejoue le jeu d'evaluation contre une instance de MegsLab et conserve tout.

Le jeu mesure ce que l'assistant repond, pas ce qu'il pourrait repondre : les
questions passent par l'API publique, comme celles d'un utilisateur. C'est la
seule facon d'inclure dans la mesure l'orchestration, le garde-fou et le cout
reel.

Les identifiants sont lus dans l'environnement : ce fichier est versionne, il
ne doit contenir aucun secret.

    MEGSLAB_API=https://api.exemple.fr \
    MEGSLAB_EMAIL=... MEGSLAB_MOT_DE_PASSE=... \
    python evaluation/lancer.py evaluation/jeu.json resultats.json
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

DELAI_SECONDES = 180


class ErreurEvaluation(RuntimeError):
    """Le jeu n'a pas pu etre lance : configuration ou API hors d'atteinte."""


class ClientApi:
    """Le strict necessaire pour poser des questions a une instance."""

    def __init__(self, base: str) -> None:
        self._base = base.rstrip("/")
        self._jeton: str | None = None

    def connecter(self, email: str, mot_de_passe: str) -> None:
        code, corps = self._appeler(
            "/auth/connexion", {"email": email, "mot_de_passe": mot_de_passe}
        )
        if code != 200 or "jeton" not in corps:
            raise ErreurEvaluation(f"Connexion refusee (HTTP {code}). Verifiez les identifiants.")
        self._jeton = corps["jeton"]

    def premier_espace(self) -> str:
        _, espaces = self._appeler("/espaces")
        if not espaces:
            raise ErreurEvaluation("Ce compte n'a acces a aucun espace de travail.")
        return espaces[0]["id"]

    def ouvrir_conversation(self, espace: str, titre: str) -> str:
        _, conv = self._appeler(f"/espaces/{espace}/conversations", {"titre": titre})
        return conv["id"]

    def poser(self, espace: str, conversation: str, texte: str) -> tuple[int, dict]:
        return self._appeler(
            f"/espaces/{espace}/conversations/{conversation}/questions", {"texte": texte}
        )

    def _appeler(self, chemin: str, corps: dict | None = None) -> tuple[int, dict]:
        donnees = json.dumps(corps).encode() if corps is not None else None
        requete = urllib.request.Request(
            self._base + chemin, data=donnees, method="POST" if donnees else "GET"
        )
        requete.add_header("Content-Type", "application/json")
        if self._jeton:
            requete.add_header("Authorization", f"Bearer {self._jeton}")
        try:
            with urllib.request.urlopen(requete, timeout=DELAI_SECONDES) as reponse:
                return reponse.status, json.loads(reponse.read() or b"{}")
        except urllib.error.HTTPError as erreur:
            return erreur.code, json.loads(erreur.read() or b"{}")
        except urllib.error.URLError as erreur:
            raise ErreurEvaluation(f"API injoignable : {erreur.reason}") from erreur


def _reglages() -> tuple[str, str, str]:
    manquants = [
        nom
        for nom in ("MEGSLAB_API", "MEGSLAB_EMAIL", "MEGSLAB_MOT_DE_PASSE")
        if not os.environ.get(nom)
    ]
    if manquants:
        raise ErreurEvaluation("Variables d'environnement absentes : " + ", ".join(manquants))
    return (
        os.environ["MEGSLAB_API"],
        os.environ["MEGSLAB_EMAIL"],
        os.environ["MEGSLAB_MOT_DE_PASSE"],
    )


def lancer(chemin_jeu: str, chemin_sortie: str) -> None:
    base, email, mot_de_passe = _reglages()
    client = ClientApi(base)
    client.connecter(email, mot_de_passe)
    espace = client.premier_espace()
    conversation = client.ouvrir_conversation(espace, "Jeu d'evaluation")
    print(f"espace {espace}, conversation {conversation}\n")

    entrees = json.load(open(chemin_jeu, encoding="utf-8"))
    resultats = []
    for rang, entree in enumerate(entrees, 1):
        depart = time.time()
        code, reponse = client.poser(espace, conversation, entree["question"])
        ecoule = time.time() - depart
        resultats.append(_ligne(rang, entree, code, reponse, ecoule))
        _tracer(resultats[-1], entree, code, ecoule)
        # Ecrit a chaque question : une coupure en cours de jeu ne doit pas
        # couter les reponses deja obtenues, qui sont payantes.
        json.dump(
            resultats, open(chemin_sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1
        )

    _resumer(resultats)


def _ligne(rang: int, entree: dict, code: int, reponse: dict, ecoule: float) -> dict:
    return {
        "n": rang,
        "question": entree["question"],
        "niveau": entree.get("niveau"),
        "famille": entree.get("famille"),
        "piege": entree.get("piege"),
        "sql_reference": entree["sql_reference"],
        "code_http": code,
        "sql_produit": reponse.get("sql"),
        "nb_lignes": reponse.get("nb_lignes"),
        "reponse": reponse.get("reponse"),
        "resultat": reponse.get("resultat"),
        "cout": reponse.get("cout_dollars"),
        "duree_ms": reponse.get("duree_ms"),
        "graphique": bool(reponse.get("graphique")),
        "etapes": reponse.get("etapes"),
        "secondes_mesurees": round(ecoule, 1),
    }


def _tracer(ligne: dict, entree: dict, code: int, ecoule: float) -> None:
    etat = "SQL" if ligne["sql_produit"] else ("REFUS" if code == 201 else f"HTTP {code}")
    lignes = ligne["nb_lignes"] if ligne["nb_lignes"] is not None else "-"
    print(
        f"{ligne['n']:2}. [{etat:5}] {ecoule:5.1f}s  {(ligne['cout'] or 0):.4f}$  "
        f"{lignes:>4} lig  {entree['question'][:52]}"
    )


def _resumer(resultats: list[dict]) -> None:
    avec_sql = [r for r in resultats if r["sql_produit"]]
    print(f"\n{len(avec_sql)}/{len(resultats)} ont produit du SQL")
    print(f"cout total   : {sum(r['cout'] or 0 for r in resultats):.4f} $")
    if avec_sql:
        moyenne = sum(r["duree_ms"] or 0 for r in avec_sql) / len(avec_sql) / 1000
        print(f"latence moy. : {moyenne:.1f} s")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    try:
        lancer(sys.argv[1], sys.argv[2])
    except ErreurEvaluation as erreur:
        print(f"Echec : {erreur}", file=sys.stderr)
        sys.exit(1)
