"""Hán Việt provenance and administrator audit."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0009_hanviet_sources"
down_revision = "0008_entry_version"
branch_labels = depends_on = None


def upgrade():
    op.add_column("kanji", sa.Column("hanviet_source", sa.Text(), nullable=True))
    op.create_table(
        "kanji_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("char", sa.String(1), sa.ForeignKey("kanji.char"), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("old", JSONB(), nullable=False),
        sa.Column("new", JSONB(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_kanji_edits_char", "kanji_edits", ["char", "id"])


def downgrade():
    op.drop_table("kanji_edits")
    op.drop_column("kanji", "hanviet_source")
