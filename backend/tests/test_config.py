"""Le durcissement du demarrage : en production, une configuration a trous refuse de partir."""

import pytest

from app.core.config import ConfigurationIncomplete, Settings, _exiger_les_secrets

CHAMPS_EXIGES = (
    "jwt_secret",
    "warehouse_postgres_database",
    "warehouse_postgres_username",
    "warehouse_postgres_password",
)
VARIABLES_EXIGEES = tuple(champ.upper() for champ in CHAMPS_EXIGES)

SECRETS_COMPLETS = {
    "environnement": "production",
    "jwt_secret": "un-secret-de-test",
    "warehouse_postgres_database": "warehouse",
    "warehouse_postgres_username": "megslab",
    "warehouse_postgres_password": "motdepasse",
}


def test_une_configuration_de_production_complete_demarre() -> None:
    _exiger_les_secrets(Settings(**SECRETS_COMPLETS))


@pytest.mark.parametrize(("champ", "variable"), zip(CHAMPS_EXIGES, VARIABLES_EXIGEES))
def test_un_secret_manquant_en_production_empeche_le_demarrage(champ: str, variable: str) -> None:
    reglages = Settings(**{**SECRETS_COMPLETS, champ: ""})
    with pytest.raises(ConfigurationIncomplete) as refus:
        _exiger_les_secrets(reglages)
    # Le message doit nommer la variable a poser : sinon il faut fouiller le code.
    assert variable in str(refus.value)


def test_le_message_de_refus_nomme_toutes_les_variables_manquantes() -> None:
    # Tous les champs sont passes explicitement : `Settings()` lit sinon le .env
    # du depot et l'environnement du poste, et le test dirait alors quelque chose
    # sur la machine qui l'execute plutot que sur le code.
    reglages = Settings(**{**SECRETS_COMPLETS, **dict.fromkeys(CHAMPS_EXIGES, "")})
    with pytest.raises(ConfigurationIncomplete) as refus:
        _exiger_les_secrets(reglages)
    for variable in VARIABLES_EXIGEES:
        assert variable in str(refus.value)


def test_hors_production_l_environnement_n_est_pas_considere_comme_tel() -> None:
    assert not Settings().en_production
    assert Settings(environnement="Production").en_production
