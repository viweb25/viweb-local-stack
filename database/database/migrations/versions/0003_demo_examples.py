"""Local practice examples for the offline inspection demo."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "demo_examples",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("part_id", sa.String(80), nullable=False),
        sa.Column("label", sa.String(4), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("label IN ('PASS', 'FAIL')", name="ck_demo_example_label"),
    )


def downgrade():
    op.drop_table("demo_examples")
