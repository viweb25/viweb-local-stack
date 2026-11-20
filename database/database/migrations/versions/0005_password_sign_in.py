"""Add database-backed password sign-in."""

from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    path = Path(__file__).resolve().parents[1] / "sql" / "0005_password_sign_in.sql"
    for statement in path.read_text().split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.drop_table("sign_in_limits", schema="identity")
    op.drop_table("password_credentials", schema="identity")
