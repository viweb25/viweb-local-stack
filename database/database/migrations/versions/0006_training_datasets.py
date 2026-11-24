"""Store organisation-owned training datasets and their annotated photos."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE training_datasets (
            id uuid PRIMARY KEY,
            org_id uuid NOT NULL REFERENCES organisations(id),
            part_name text NOT NULL CHECK (length(btrim(part_name)) BETWEEN 1 AND 80),
            inspection_note text NOT NULL CHECK (length(inspection_note) <= 400),
            revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX training_datasets_org_updated_idx
        ON training_datasets (org_id, updated_at DESC, id)
    """)
    op.execute("""
        CREATE TABLE training_photos (
            dataset_id uuid NOT NULL REFERENCES training_datasets(id) ON DELETE CASCADE,
            id uuid NOT NULL,
            filename text NOT NULL CHECK (length(filename) BETWEEN 1 AND 255),
            media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png')),
            digest text NOT NULL CHECK (digest ~ '^[a-f0-9]{64}$'),
            reviewed boolean NOT NULL,
            boxes jsonb NOT NULL CHECK (jsonb_typeof(boxes) = 'array'),
            position integer NOT NULL CHECK (position >= 0),
            PRIMARY KEY (dataset_id, id),
            UNIQUE (dataset_id, position)
        )
    """)


def downgrade():
    op.drop_table("training_photos")
    op.drop_table("training_datasets")
