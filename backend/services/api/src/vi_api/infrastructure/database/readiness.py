import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseReadinessRepository:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def is_ready(self) -> bool:
        try:
            async with asyncio.timeout(3):
                async with self.engine.connect() as connection:
                    revision = await connection.scalar(
                        text("SELECT version_num FROM alembic_version")
                    )
                    return revision == "0005"
        except Exception:
            return False
