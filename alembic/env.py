from alembic import context
from sqlalchemy import engine_from_config, pool

from database import Base

target_metadata = Base.metadata

config = context.config


def run_migrations_online() -> None:

    from database import _database_url

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
