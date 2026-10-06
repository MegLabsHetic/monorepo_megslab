"""Contrats des routes de notifications et du journal d'audit."""

from datetime import datetime

from pydantic import BaseModel


class NotificationReponse(BaseModel):
    id: str
    type: str
    titre: str
    corps: str
    lien: str | None
    lue: bool
    cree_le: datetime


class NotificationsReponse(BaseModel):
    non_lues: int
    notifications: list[NotificationReponse]


class EntreeJournalReponse(BaseModel):
    id: str
    action: str
    cible_type: str
    cible_id: str | None
    cible_nom: str
    detail: dict
    auteur: str
    auteur_email: str
    espace: str | None
    cree_le: datetime


class JournalReponse(BaseModel):
    total: int
    page: int
    entrees: list[EntreeJournalReponse]
