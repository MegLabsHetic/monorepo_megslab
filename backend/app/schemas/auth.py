"""Contrats d'entree/sortie des routes d'authentification."""

from pydantic import BaseModel, EmailStr, Field


class InscriptionDemande(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=8)
    nom_complet: str = Field(min_length=1)


class ConnexionDemande(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UtilisateurReponse(BaseModel):
    id: str
    email: str
    nom_complet: str

    model_config = {"from_attributes": True}


class SessionReponse(BaseModel):
    jeton: str
