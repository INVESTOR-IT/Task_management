from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

from alembic import context

import asyncio, greenlet

from app.db.base import Base
from app.core.config import settings


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
target_metadata = Base.metadata


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        url=settings.DATABASE_URL,
        poolclass=pool.NullPool,
        future=True
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_connection: context.configure(
                connection=sync_connection,
                target_metadata=target_metadata
            )
        )

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)



if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
