"""Reconnaitre ce qu'une colonne de resultat contient, sans metadonnees.

Un resultat de requete n'a que des valeurs Python : les agents ML et Viz ont
besoin de savoir si une colonne est un nombre, une date ou du texte pour
decider quoi en faire. Le meme critere sert aux deux, il vit donc ici.
"""

import re
from datetime import date, datetime
from decimal import Decimal

_MOIS_ISO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")
_ANNEE = re.compile(r"^(19|20)\d{2}$")


def est_nombre(valeur: object) -> bool:
    return isinstance(valeur, (int, float, Decimal)) and not isinstance(valeur, bool)


def est_date(valeur: object) -> bool:
    if isinstance(valeur, (date, datetime)):
        return True
    return isinstance(valeur, str) and bool(_DATE_ISO.match(valeur) or _MOIS_ISO.match(valeur))


def genre_colonne(valeurs: list[object]) -> str:
    """« nombre », « date » ou « texte », d'apres les valeurs non nulles.

    Une colonne vide est du texte : on n'en fera ni courbe ni regression.
    """
    presentes = [valeur for valeur in valeurs if valeur is not None]
    if not presentes:
        return "texte"
    if all(est_nombre(valeur) for valeur in presentes):
        return "nombre"
    if all(est_date(valeur) for valeur in presentes):
        return "date"
    return "texte"


def est_annee(valeur: object) -> bool:
    if isinstance(valeur, bool):
        return False
    if isinstance(valeur, int):
        return 1900 <= valeur <= 2100
    return isinstance(valeur, str) and bool(_ANNEE.match(valeur))
