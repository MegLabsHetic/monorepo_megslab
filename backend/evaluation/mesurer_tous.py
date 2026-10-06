"""Mesure tous les modeles d'un fournisseur en parallele, en quelques minutes.

Le banc question par question ouvrait une connexion DuckDB et reattachait
PostgreSQL a CHAQUE execution : 117 attaches par modele, 1 404 au total a
travers un tunnel unique. L'attache coutait plus que la requete.

Ici, un petit vivier de connexions deja attachees est partage par tous les
modeles, et les douze series tournent de front. Le facteur limitant redevient
ce qu'il doit etre : le temps de reponse du modele.

    OVHCLOUD_API_KEY=... python evaluation/mesurer_tous.py ovhcloud

Une connexion DuckDB n'est pas sure en acces concurrent : chaque connexion du
vivier n'est donc pretee qu'a un seul travailleur a la fois.
"""

import asyncio
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.analyste import (  # noqa: E402
    INSTRUCTIONS,
    PlanRequete,
    _demande_correction,
)
from app.agents.data import AgentData  # noqa: E402
from app.core.duckdb_engine import DuckDBEngine, _sans_secret  # noqa: E402
from app.core.errors import ErreurUtilisateur, FournisseurIndisponible  # noqa: E402
from app.core.fournisseur_anthropic import FournisseurAnthropic  # noqa: E402
from app.core.fournisseur_openai import FournisseurOpenAICompatible  # noqa: E402
from app.core.sql_guard import SqlRefuse, valider  # noqa: E402
from app.core.tarifs import CATALOGUE  # noqa: E402

SCHEMA = "demo_olist"
DOSSIER = Path(__file__).parent

# Les definitions que le schema ne porte pas, et dont l'absence explique la
# majorite des ecarts : le chiffre d'affaires avec ou sans frais de port, et
# ce qu'est un client quand une table en compte un par commande.
GLOSSAIRE = {
    ("order_items", "price"): (
        "prix de vente de l'article. Le chiffre d'affaires se calcule sur cette "
        "colonne SEULE : les frais de port sont factures au client, donc un "
        "produit, jamais une composante du chiffre d'affaires"
    ),
    ("order_items", "freight_value"): ("frais de port factures. A exclure du chiffre d'affaires"),
    ("customers", "customer_id"): (
        "identifiant technique, UNIQUE PAR COMMANDE. Ne jamais l'utiliser pour "
        "compter des clients"
    ),
    ("customers", "customer_unique_id"): (
        "le veritable identifiant du client, stable entre ses commandes. C'est "
        "lui qu'il faut compter ou regrouper pour parler de clients"
    ),
    # Volontairement descriptif, sans prescrire de filtre. Une premiere version
    # disait « delivered designe une commande effectivement livree » : les
    # modeles en ont deduit un WHERE order_status = 'delivered' sur TOUTES les
    # questions de chiffre d'affaires, que les references n'appliquent pas. Le
    # resultat etait defendable, mais ce n'etait plus la meme question.
    ("orders", "order_status"): (
        "statut de la commande, parmi « delivered », « shipped », « canceled », "
        "« unavailable ». Une annulation n'est pas un retour produit : le retour "
        "n'existe pas dans ce schema"
    ),
}
JEU = DOSSIER / "jeu-etendu.json"
CACHE = DOSSIER / ".cache-references-ordonnees.json"

# Connexions a l'entrepot maintenues ouvertes et partagees. Au-dela, le tunnel
# unique devient le goulet.
CONNEXIONS = 12
# Appels au modele de front, tous modeles confondus.
#
# Une premiere serie a 48 a produit 60 delais depasses sur 117 chez un seul
# modele : la limite du fournisseur n'est pas le debit annonce mais la file
# d'attente, et une requete qui patiente derriere quarante autres expire avant
# d'etre servie. Des pannes de banc comptees comme des echecs de modele
# rendraient la mesure fausse, pas seulement bruyante.
APPELS = 40
DECIMALES = 2

# Les quatre facons d'avoir raison. Elles sont distinguees dans le detail pour
# qu'un lecteur puisse recalculer le taux en n'en retenant que la premiere.
JUSTES = ("juste", "juste_en_plus", "juste_classement", "juste_sommet")


class _Erreur:
    """Le minimum que `_demande_correction` attend d'une erreur du moteur."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        self.raison = detail


_ETIQUETTE_TEMPS = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?(?:[T ](\d{2}):(\d{2}):(\d{2}))?")


def _temps(texte: str) -> str | None:
    """Ramene une etiquette de temps a une forme unique, ou None si ce n'en est pas une.

    Constate en reel le 23 septembre 2026 : la reference groupe par
    DATE_TRUNC('month', ...) et rend un horodatage « 2017-01-01 00:00:00 »,
    le modele groupe par STRFTIME('%Y-%m') et rend « 2017-01 ». Les deux
    designent le meme mois, et c'est le meme regroupement. Les comparer en
    texte mesurerait le format d'affichage, pas la justesse de la requete.
    """
    trouve = _ETIQUETTE_TEMPS.fullmatch(texte)
    if not trouve:
        return None
    annee, mois, jour, heure, minute, seconde = trouve.groups()
    return f"{annee}-{mois}-{jour or '01'} {heure or '00'}:{minute or '00'}:{seconde or '00'}"


def normaliser(lignes) -> list:
    """Rend les cellules comparables, sans toucher a l'ordre des lignes.

    L'ordre est conserve parce que deux des trois criteres de justesse en
    dependent : il distingue « le modele a rendu le classement complet » de
    « le modele a rendu autre chose ».
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
                texte = str(valeur).strip()
                cellules.append(_nombre(texte) or _temps(texte) or texte)
        propres.append(cellules)
    return propres


_NOMBRE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _nombre(texte: str) -> str | None:
    """Une chaine qui represente un nombre est comparee comme un nombre.

    Constate en reel le 23 septembre 2026 : un modele rend le trimestre en
    texte (CAST(... AS VARCHAR), « 1 »), la reference le rend en nombre
    (« 1.00 » apres arrondi). Meme valeur, meme regroupement ; les distinguer
    mesurerait un choix de type, pas la justesse de la requete. La forme est
    restreinte aux decimaux simples : « nan », « inf » ou une notation
    scientifique restent du texte.
    """
    if not _NOMBRE.fullmatch(texte):
        return None
    return f"{round(float(texte), DECIMALES):.{DECIMALES}f}"


def identique(obtenu: list, attendu: list) -> bool:
    """Memes lignes, quel que soit leur ordre."""
    return sorted(obtenu) == sorted(attendu)


def contient(obtenu: list, attendu: list) -> bool:
    """Chaque ligne attendue se retrouve-t-elle dans une ligne produite ?

    Tolere les colonnes supplementaires, pas les valeurs manquantes. Exige
    autant de lignes de part et d'autre : un modele qui rend tout le tableau
    la ou dix lignes etaient demandees n'a pas repondu a la question.
    """
    if not attendu or len(obtenu) != len(attendu):
        return False
    restantes = [set(ligne) for ligne in obtenu]
    for ligne in attendu:
        voulu = set(ligne)
        for i, disponible in enumerate(restantes):
            if voulu <= disponible:
                restantes.pop(i)
                break
        else:
            return False
    return True


def classement_complet(obtenu: list, attendu: list) -> bool:
    """La reference est-elle le sommet du classement produit ?

    Constate en reel le 23 septembre 2026 : « A quelle heure nos clients
    commandent-ils le plus ? » a pour reference un LIMIT 5 que la question
    n'enonce nulle part. Un modele qui rend les vingt-quatre heures classees
    a repondu, et avec plus de matiere. Le compter faux mesurerait le choix
    arbitraire de notre reference, pas sa competence.

    L'ordre compte ici : les lignes attendues doivent etre EN TETE du
    resultat produit, pas dispersees dedans.
    """
    if not attendu or len(obtenu) <= len(attendu):
        return False
    return all(set(a) <= set(o) for o, a in zip(obtenu, attendu))


def sommet_du_classement(obtenu: list, attendu: list) -> bool:
    """Le modele a-t-il rendu la seule ligne que la question demandait ?

    Reservee aux questions marquees « sommet » dans le jeu d'evaluation :
    celles qui posent un superlatif au singulier (« quel jour recoit le plus
    de commandes ? »). La reference les classe toutes ; la question n'en
    demande qu'une. Le marqueur est dans les donnees, pas devine par le code :
    un lecteur peut ouvrir le fichier et contester chaque cas.
    """
    if not obtenu or not attendu or len(obtenu) >= len(attendu):
        return False
    return all(set(a) <= set(o) for o, a in zip(obtenu, attendu))


class Vivier:
    """Des connexions a l'entrepot, deja attachees, pretees une a la fois."""

    def __init__(self, combien: int) -> None:
        moteur = DuckDBEngine(SCHEMA)
        self._libres: asyncio.Queue = asyncio.Queue()
        self._connexions = [moteur._connexion_verrouillee() for _ in range(combien)]
        for c in self._connexions:
            self._libres.put_nowait(c)

    async def executer(self, sql: str, lignes_max: int = 5000):
        connexion = await self._libres.get()
        try:
            return await asyncio.to_thread(self._lire, connexion, sql, lignes_max)
        finally:
            self._libres.put_nowait(connexion)

    @staticmethod
    def _lire(connexion, sql: str, lignes_max: int):
        curseur = connexion.execute(sql)
        colonnes = [d[0] for d in curseur.description or []]
        return colonnes, curseur.fetchmany(lignes_max)

    def fermer(self) -> None:
        for c in self._connexions:
            c.close()


async def une_question(llm, vivier, verrou, schema_texte, entree, references) -> dict:
    impossible = entree["sql_reference"] == "IMPOSSIBLE"
    base = {
        "question": entree["question"],
        "famille": entree["famille"],
        "niveau": entree["niveau"],
        "impossible": impossible,
        "sql_produit": "",
        "cout": 0.0,
        "verdict": "",
        "raison": "",
        "corrigee": False,
    }
    # Une question exclue par l'audit du jeu n'est pas posee : son verdict ne
    # serait pas automatisable, et le dire coute moins qu'un faux « faux ».
    if entree.get("exclue"):
        return {**base, "verdict": "exclue", "raison": entree["exclue"][:120]}

    # Le schema va dans les INSTRUCTIONS, pas dans la question : c'est ce que
    # fait l'agent Analyste, et un modele ne traite pas de la meme facon ce
    # qu'on lui donne en consigne et ce qu'on lui pose en question.
    instructions = f"{INSTRUCTIONS}\n\nSchema disponible :\n{schema_texte}"
    texte = entree["question"]

    async def proposer(demande):
        async with verrou:
            return await llm.repondre(
                instructions=instructions, question=demande, format_sortie=PlanRequete
            )

    try:
        reponse = await proposer(texte)
    except (FournisseurIndisponible, ErreurUtilisateur) as erreur:
        return {**base, "verdict": "panne", "raison": str(erreur)[:110]}

    base["cout"] = reponse.consommation.cout_dollars
    base["sql_produit"] = reponse.contenu.sql.strip()

    if not base["sql_produit"]:
        if impossible:
            return {**base, "verdict": "refus_correct", "raison": "refus attendu"}
        return {**base, "verdict": "refus_a_tort", "raison": reponse.contenu.explication[:110]}
    if impossible:
        return {**base, "verdict": "aurait_du_refuser", "raison": "a produit du SQL"}

    try:
        sql = valider(base["sql_produit"])
    except SqlRefuse as refus:
        return {**base, "verdict": "refuse_garde_fou", "raison": refus.raison[:110]}

    try:
        _, lignes = await vivier.executer(sql)
    except Exception as erreur:  # noqa: BLE001
        # L'agent Analyste a droit a UNE reprise : il voit l'erreur du moteur
        # et repropose. Ne pas la reproduire ici mesurerait un produit ampute,
        # et penaliserait precisement les modeles qui savent se corriger.
        detail = _sans_secret(str(erreur).splitlines()[0][:200]) if str(erreur) else "echec"
        try:
            reponse = await proposer(_demande_correction(texte, sql, _Erreur(detail)))
        except (FournisseurIndisponible, ErreurUtilisateur) as echec:
            return {**base, "verdict": "panne", "raison": str(echec)[:110]}
        base["cout"] += reponse.consommation.cout_dollars
        base["sql_produit"] = reponse.contenu.sql.strip()
        base["corrigee"] = True
        if not base["sql_produit"]:
            return {**base, "verdict": "refus_a_tort", "raison": "refus apres correction"}
        try:
            sql = valider(base["sql_produit"])
            _, lignes = await vivier.executer(sql)
        except Exception as encore:  # noqa: BLE001
            # Une panne du tunnel fait citer le DSN par DuckDB, mot de passe
            # compris. Ces fichiers sont versionnes : le filtrer ici, comme le
            # produit le fait dans ses journaux.
            raison = _sans_secret(str(encore).splitlines()[0][:110]) if str(encore) else "echec"
            return {**base, "verdict": "erreur_moteur", "raison": raison}

    attendu = references.get(entree["question"])
    if attendu is None:
        return {**base, "verdict": "reference_absente", "raison": "hors cache"}

    obtenu = normaliser(lignes)
    if identique(obtenu, attendu):
        return {**base, "verdict": "juste", "raison": "identique"}
    if contient(obtenu, attendu):
        # Le modele a rendu les valeurs demandees, plus du contexte : un
        # identifiant de categorie a cote du comptage, par exemple. Repondre
        # plus que demande n'est pas repondre faux.
        return {**base, "verdict": "juste_en_plus", "raison": "valeurs attendues + contexte"}
    if classement_complet(obtenu, attendu):
        return {
            **base,
            "verdict": "juste_classement",
            "raison": "classement complet, reference en tete",
        }
    if entree.get("sommet") and sommet_du_classement(obtenu, attendu):
        return {
            **base,
            "verdict": "juste_sommet",
            "raison": "la ligne demandee, sans le classement",
        }
    if len(obtenu) != len(attendu):
        raison = f"{len(obtenu)} ligne(s) contre {len(attendu)}"
    else:
        raison = f"{sum(1 for x, y in zip(obtenu, attendu) if x != y)} ligne(s) differente(s)"
    return {**base, "verdict": "faux", "raison": raison}


async def un_modele(
    fournisseur, modele, cle, vivier, verrou, schema_texte, entrees, refs, avancement
) -> dict:
    depart = time.perf_counter()
    llm = _fournisseur(fournisseur, modele, cle)

    async def suivie(entree):
        ligne = await une_question(llm, vivier, verrou, schema_texte, entree, refs)
        avancement[modele] = avancement.get(modele, 0) + 1
        return ligne

    lignes = await asyncio.gather(*(suivie(e) for e in entrees))
    possibles = [r for r in lignes if not r["impossible"] and r["verdict"] != "exclue"]
    impossibles = [r for r in lignes if r["impossible"]]
    synthese = {
        "fournisseur": fournisseur,
        "modele": modele,
        "date": date.today().isoformat(),
        "secondes": round(time.perf_counter() - depart, 1),
        "questions": len(lignes),
        "questions_possibles": len(possibles),
        "justes": sum(1 for r in lignes if r["verdict"] in JUSTES),
        "justes_stricts": sum(1 for r in lignes if r["verdict"] == "juste"),
        "justes_avec_contexte": sum(1 for r in lignes if r["verdict"] == "juste_en_plus"),
        "justes_classement": sum(1 for r in lignes if r["verdict"] == "juste_classement"),
        "justes_sommet": sum(1 for r in lignes if r["verdict"] == "juste_sommet"),
        "questions_impossibles": len(impossibles),
        "refus_corrects": sum(1 for r in impossibles if r["verdict"] == "refus_correct"),
        "cout_total_dollars": round(sum(r["cout"] for r in lignes), 4),
        "detail": lignes,
    }
    suffixe = "-glossaire" if os.environ.get("GLOSSAIRE") else ""
    (DOSSIER / f"mesure-{synthese['date']}-{fournisseur}-{modele}{suffixe}.json").write_text(
        json.dumps(synthese, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"  {modele:38} {synthese['justes']:3}/{len(possibles)} justes, "
        f"{synthese['refus_corrects']}/{len(impossibles)} refus, "
        f"{synthese['cout_total_dollars']:.4f} $, {synthese['secondes']:.0f} s",
        flush=True,
    )
    return synthese


def _fournisseur(nom: str, modele: str, cle: str):
    """Le fournisseur historique n'expose pas d'API compatible OpenAI.

    Le mesurer ici, sous le meme protocole et sur les memes questions que les
    modeles ouverts, est la seule facon de rendre les taux comparables : un
    chiffre obtenu sur quinze questions via l'API du produit ne se compare pas
    a un chiffre obtenu sur cinquante via ce banc.
    """
    if nom == "anthropic":
        return FournisseurAnthropic(cle_api=cle, modele=modele)
    return FournisseurOpenAICompatible(nom=nom, modele=modele, cle_api=cle)


def references(vivier_moteur, entrees) -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    cache = {}
    for entree in entrees:
        if entree["sql_reference"] == "IMPOSSIBLE":
            continue
        resultat = vivier_moteur.executer(valider(entree["sql_reference"]))
        cache[entree["question"]] = normaliser(resultat.lignes)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


async def principal(fournisseur: str) -> None:
    cle = os.environ.get(f"{fournisseur.upper()}_API_KEY", "")
    if not cle:
        print(f"Aucune cle dans {fournisseur.upper()}_API_KEY.", file=sys.stderr)
        sys.exit(1)

    depart = time.perf_counter()
    moteur = DuckDBEngine(SCHEMA)
    entrees = json.load(open(JEU, encoding="utf-8"))
    refs = references(moteur, entrees)
    contexte = AgentData(moteur).decrire()
    glossaire = GLOSSAIRE if os.environ.get("GLOSSAIRE") else None
    schema_texte = contexte.texte(glossaire)
    if glossaire:
        print(f"glossaire metier actif : {len(glossaire)} definitions", flush=True)
    modeles = sorted(m for (f, m) in CATALOGUE if f == fournisseur)
    if os.environ.get("MODELES"):
        voulus = {m.strip() for m in os.environ["MODELES"].split(",")}
        modeles = [m for m in modeles if m in voulus]
    if os.environ.get("ECHANTILLON"):
        # Echantillon stratifie : on prend les premieres questions de chaque
        # famille, pour qu'un tirage reduit reste representatif des dix familles
        # plutot que de concentrer le hasard sur trois d'entre elles.
        combien = int(os.environ["ECHANTILLON"])
        par_famille: dict[str, list] = {}
        for e in entrees:
            par_famille.setdefault(e["famille"], []).append(e)
        quota = max(1, combien // len(par_famille))
        retenues = [e for liste in par_famille.values() for e in liste[:quota]]
        entrees = retenues[:combien] if len(retenues) > combien else retenues
        print(
            f"echantillon stratifie : {len(entrees)} questions " f"sur {len(par_famille)} familles",
            flush=True,
        )
    print(f"{len(modeles)} modeles, {len(entrees)} questions, {len(refs)} references\n", flush=True)

    vivier = Vivier(CONNEXIONS)
    verrou = asyncio.Semaphore(APPELS)
    avancement: dict[str, int] = {}

    async def afficher():
        while True:
            await asyncio.sleep(30)
            fait = sum(avancement.values())
            total = len(modeles) * len(entrees)
            print(f"    ... {fait}/{total} questions traitees", flush=True)

    veilleur = asyncio.create_task(afficher())
    try:
        syntheses = await asyncio.gather(
            *(
                un_modele(
                    fournisseur, m, cle, vivier, verrou, schema_texte, entrees, refs, avancement
                )
                for m in modeles
            )
        )
    finally:
        veilleur.cancel()
        vivier.fermer()

    print(f"\n{'=' * 92}")
    print(f"  {'modele':38} {'justes':>10} {'refus':>8} {'cout':>9} {'duree':>7}")
    print("-" * 92)
    for s in sorted(syntheses, key=lambda x: -x["justes"]):
        part = 100 * s["justes"] / max(1, s["questions_possibles"])
        print(
            f"  {s['modele']:38} {s['justes']:4}/{s['questions_possibles']:<3} {part:4.0f}% "
            f"{s['refus_corrects']:3}/{s['questions_impossibles']:<3} "
            f"{s['cout_total_dollars']:8.4f}$ {s['secondes']:6.0f}s"
        )
    total = sum(s["cout_total_dollars"] for s in syntheses)
    print("-" * 92)
    print(f"  {len(modeles)} modeles, {total:.4f} $, {time.perf_counter() - depart:.0f} s au total")
    print("=" * 92)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    asyncio.run(principal(sys.argv[1]))
