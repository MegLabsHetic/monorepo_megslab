"""Contrats d'entree/sortie des routes d'authentification et de profil."""

from pydantic import BaseModel, EmailStr, Field


class InscriptionDemande(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=8)
    nom_complet: str = Field(min_length=1)


class ConnexionDemande(BaseModel):
    email: EmailStr
    mot_de_passe: str


class OrganisationDuProfil(BaseModel):
    id: str
    nom: str
    role: str


class UtilisateurReponse(BaseModel):
    id: str
    email: str
    nom_complet: str
    est_super_admin: bool = False
    doit_changer_mot_de_passe: bool = False
    organisation: OrganisationDuProfil | None = None

    model_config = {"from_attributes": True}


class SessionReponse(BaseModel):
    jeton: str


class ProfilModification(BaseModel):
    nom_complet: str = Field(min_length=1, max_length=255)


class MotDePasseModification(BaseModel):
    actuel: str
    nouveau: str = Field(min_length=8)


class InvitationInfoReponse(BaseModel):
    """Ce qu'on montre a quelqu'un qui ouvre un lien d'invitation, avant qu'il
    ne s'engage : ou il va, sous quel e-mail, et s'il a deja un compte."""

    organisation: str
    email: str
    role: str
    compte_existant: bool


class InvitationAcceptation(BaseModel):
    # Requis seulement pour un e-mail qui n'a pas encore de compte.
    nom_complet: str | None = None
    mot_de_passe: str | None = Field(default=None, min_length=8)
