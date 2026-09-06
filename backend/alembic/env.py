from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import get_settings
from app.core.database import Base

# Importer chaque module de modele enregistre sa table sur Base.metadata.
# Sans cet import, autogenerate ne verrait aucune table.
from app.models import (  # noqa: F401
    audit_log,
    conversation,
    dashboard,
    data_source,
    invitation,
    membership,
    notification,
    organization,
    question,
    user,
    workspace,
    workspace_access,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url_synchrone() -> str:
    """Alembic migre en synchrone ; l'app tourne en async. On derive l'un de l'autre
    plutot que de dupliquer l'URL dans alembic.ini (et risquer qu'elle diverge)."""
    return get_settings().database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")


def run_migrations_offline() -> None:
    context.configure(
        url=_url_synchrone(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _url_synchrone()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
