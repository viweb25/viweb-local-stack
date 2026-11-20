"""Opt-in integration checks against a migrated disposable development database."""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

URL = os.getenv("DATABASE_TEST_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Set DATABASE_TEST_URL to a migrated test database")


def test_migrations_and_diagnostic_functions():
    async def check():
        engine = create_async_engine(URL)
        try:
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(text("SELECT platform.usp_schema_version()")) == "0005"
                )
                assert await connection.scalar(text("SELECT platform.usp_migration_table_exists()"))
                assert await connection.scalar(text("SELECT platform.usp_database_name()"))
                assert (
                    await connection.scalar(text("SELECT platform.usp_database_size_bytes()")) > 0
                )
                assert await connection.scalar(text("SELECT platform.usp_server_version()"))
                assert await connection.scalar(text("SELECT platform.usp_connection_count()")) >= 1
                assert (
                    await connection.scalar(text("SELECT platform.usp_active_connection_count()"))
                    >= 1
                )
                assert isinstance(
                    await connection.scalar(text("SELECT platform.usp_transaction_read_only()")),
                    bool,
                )
                assert isinstance(
                    await connection.scalar(text("SELECT platform.usp_is_replica()")), bool
                )
                sizes = await connection.execute(text("SELECT * FROM platform.usp_table_sizes()"))
                assert "public.organisations" in {row.table_name for row in sizes}
                routines = await connection.execute(
                    text("""
                    SELECT p.proname, p.prosecdef FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'platform'
                """)
                )
                rows = list(routines)
                assert len(rows) == 10
                assert not any(row.prosecdef for row in rows)
        finally:
            await engine.dispose()

    asyncio.run(check())
