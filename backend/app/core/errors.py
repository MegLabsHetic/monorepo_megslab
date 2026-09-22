"""Erreur destinee a etre affichee telle quelle a l'utilisateur, en francais.

Toute autre exception reste une erreur 500 generique cote API : le detail
technique va dans les logs, jamais dans la reponse HTTP.
"""


class ErreurUtilisateur(Exception):
    def __init__(self, message: str, code_http: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code_http = code_http


class FournisseurIndisponible(Exception):
    """Un fournisseur de modele n'a pas pu repondre, pour une raison de disponibilite.

    C'est la SEULE condition qui autorise un rabattement vers le fournisseur
    suivant : delai depasse, coupure reseau, 5xx, limite de debit.

    Ne jamais lever cette erreur pour un refus du modele ni pour une sortie mal
    formee. Ce sont des resultats, pas des pannes : les rejouer ailleurs
    masquerait un defaut au lieu de le montrer, ce que ce produit s'interdit.
    """

    def __init__(self, fournisseur: str, raison: str) -> None:
        super().__init__(f"{fournisseur} : {raison}")
        self.fournisseur = fournisseur
        self.raison = raison
