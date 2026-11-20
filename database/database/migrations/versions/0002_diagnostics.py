"""Versioned developer diagnostics; SQL is applied exactly once by Alembic."""

from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


NAMES = (
    "database_name",
    "database_size_bytes",
    "server_version",
    "schema_version",
    "connection_count",
    "active_connection_count",
    "transaction_read_only",
    "is_replica",
    "table_sizes",
    "migration_table_exists",
)


def upgrade():
    path = Path(__file__).resolve().parents[2] / "functions/0002_diagnostics.sql"
    # Each command is independent; asyncpg does not accept multiple prepared commands.
    from sqlalchemy import text

    sql = path.read_text()
    # SQL function bodies contain no semicolons; migration-owned file only.
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(text(statement))


def downgrade():
    for name in reversed(NAMES):
        op.execute(f"DROP FUNCTION platform.usp_{name}()")
    op.execute("DROP SCHEMA platform")
