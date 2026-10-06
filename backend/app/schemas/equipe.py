"""Contrats des routes d'equipe : membres, roles, invitations."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AccesDemandeSchema(BaseModel):
    espace_id: str
    role: str


class AccesMembreReponse(BaseModel):
    espace_id: str
    espace_nom: str
    role: str


class MembreReponse(BaseModel):
    id: str
    email: str
    nom_complet: str
    role: str
    actif: bool
    doit_changer_mot_de_passe: bool
    acces: list[AccesMembreReponse]
    cree_le: datetime


class MembreCreation(BaseModel):
    email: EmailStr
    nom_complet: str = Field(min_length=1)
    mot_de_passe_temporaire: str = Field(min_length=8)
    role: str = "member"
    acces: list[AccesDemandeSchema] = Field(default_factory=list)


class RoleModification(BaseModel):
    role: str


class InvitationDemande(BaseModel):
    email: EmailStr
    role: str = "member"
    acces: list[AccesDemandeSchema] = Field(default_factory=list)


class InvitationReponse(BaseModel):
    id: str
    email: str
    role: str
    acces: list[AccesDemandeSchema]
    # Le jeton n'est rendu qu'aux admins de l'organisation, qui construisent le
    # lien et le transmettent eux-memes : aucun e-mail ne part d'ici.
    jeton: str
    expire_le: datetime
    acceptee_le: datetime | None
    cree_le: datetime
