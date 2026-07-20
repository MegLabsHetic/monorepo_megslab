"""Erreur destinee a etre affichee telle quelle a l'utilisateur, en francais.

Toute autre exception reste une erreur 500 generique cote API : le detail
technique va dans les logs, jamais dans la reponse HTTP.
"""


class ErreurUtilisateur(Exception):
    def __init__(self, message: str, code_http: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code_http = code_http
