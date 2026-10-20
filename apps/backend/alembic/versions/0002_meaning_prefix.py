"""Indexes for case-insensitive short Latin meaning prefixes."""

from alembic import op

revision = "0002_meaning_prefix"
down_revision = "0001_p0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE INDEX ix_senses_gloss_prefix ON word_senses (lower(gloss) text_pattern_ops)")
    op.execute(
        "CREATE INDEX ix_entries_search_prefix ON textbook_entries "
        "(lower(search_text) text_pattern_ops)"
    )


def downgrade():
    op.execute("DROP INDEX ix_entries_search_prefix")
    op.execute("DROP INDEX ix_senses_gloss_prefix")
