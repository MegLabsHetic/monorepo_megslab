"""Contrats des routes de conversation."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationReponse(BaseModel):
    id: str
    titre: str
    epinglee: bool
    nb_questions: int
    auteur: str
    auteur_id: str
    cree_le: datetime
    maj_le: datetime


class ConversationCreation(BaseModel):
    titre: str | None = Field(default=None, max_length=120)


class ConversationModification(BaseModel):
    titre: str | None = Field(default=None, min_length=1, max_length=120)
    epinglee: bool | None = None
