"""Store entry lemmas separately from display/search text."""

from alembic import op

revision = "0003_entry_lemmas"
down_revision = "0002_meaning_prefix"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE textbook_entries ADD COLUMN lemmas text[] NOT NULL DEFAULT '{}'")
    op.execute("CREATE INDEX ix_entries_lemmas ON textbook_entries USING gin (lemmas)")


def downgrade():
    op.execute("DROP INDEX ix_entries_lemmas")
    op.execute("ALTER TABLE textbook_entries DROP COLUMN lemmas")
