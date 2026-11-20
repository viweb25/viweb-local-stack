import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine


def configure(connection=None):
    options = {"target_metadata": None, "compare_type": True}
    if connection is None:
        options.update(url=os.environ["DATABASE_URL"], literal_binds=True)
    else:
        options["connection"] = connection
    context.configure(**options)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as connection:
        await connection.run_sync(configure)
    await engine.dispose()


if context.is_offline_mode():
    configure()
else:
    asyncio.run(online())
