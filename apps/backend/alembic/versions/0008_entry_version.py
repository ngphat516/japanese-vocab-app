"""Optimistic concurrency for manual entry edits."""

import sqlalchemy as sa

from alembic import op

revision = "0008_entry_version"
down_revision = "0007_word_edits"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "textbook_entries", sa.Column("version", sa.Integer(), nullable=False, server_default="1")
    )


def downgrade():
    op.drop_column("textbook_entries", "version")
