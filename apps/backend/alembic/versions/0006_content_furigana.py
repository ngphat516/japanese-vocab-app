"""Derived furigana content, preserving the original OCR."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_content_furigana"
down_revision = "0005_notebook"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "textbook_entries", sa.Column("content_furigana", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "textbook_entries",
        sa.Column("auto_furigana", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade():
    op.drop_column("textbook_entries", "auto_furigana")
    op.drop_column("textbook_entries", "content_furigana")
