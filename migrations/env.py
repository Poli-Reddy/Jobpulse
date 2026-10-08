from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.attributes.get("database_url") or get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = config.attributes.get("database_url") or get_settings().database_url
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = str(database_url).replace("%", "%%")
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        pool_pre_ping=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
