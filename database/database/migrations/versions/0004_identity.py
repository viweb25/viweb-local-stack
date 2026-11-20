"""Create the SaaS identity schema from the reviewed PostgreSQL statements."""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    path = Path(__file__).resolve().parents[1] / "sql" / "0004_identity.sql"
    for statement in path.read_text().split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for table in ("sessions", "memberships", "external_identities", "users"):
        op.drop_table(table, schema="identity")
    op.execute("DROP SCHEMA identity")
