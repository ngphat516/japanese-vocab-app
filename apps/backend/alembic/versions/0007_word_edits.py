"""Audit administrator changes to word fields."""

import sqlalchemy as sa

from alembic import op

revision = "0007_word_edits"
down_revision = "0006_content_furigana"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "word_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("old", sa.Text(), nullable=False),
        sa.Column("new", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_word_edits_word_id", "word_edits", ["word_id", "id"])


def downgrade():
    op.drop_table("word_edits")
