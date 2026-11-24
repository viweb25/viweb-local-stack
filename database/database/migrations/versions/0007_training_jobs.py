"""Persist training jobs and immutable dataset snapshots."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE training_jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            dataset_id uuid NOT NULL REFERENCES training_datasets(id),
            dataset_revision integer NOT NULL CHECK (dataset_revision > 0),
            snapshot jsonb NOT NULL,
            status text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
            error text,
            created_at timestamptz NOT NULL DEFAULT now(),
            started_at timestamptz,
            finished_at timestamptz
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX training_jobs_active_dataset_idx
        ON training_jobs (dataset_id) WHERE status IN ('queued', 'running')
    """)
    op.execute("""
        CREATE INDEX training_jobs_dataset_created_idx
        ON training_jobs (dataset_id, created_at DESC, id)
    """)


def downgrade():
    op.drop_table("training_jobs")
