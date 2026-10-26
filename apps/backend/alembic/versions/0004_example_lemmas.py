"""Index only Japanese example and usage fields for consistent entry counts."""

from alembic import op

revision = "0004_example_lemmas"
down_revision = "0003_entry_lemmas"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE textbook_entries ADD COLUMN example_lemmas text[] NOT NULL DEFAULT '{}'"
    )
    op.execute(
        "CREATE INDEX ix_entries_example_lemmas ON textbook_entries USING gin (example_lemmas)"
    )


def downgrade():
    op.execute("DROP INDEX ix_entries_example_lemmas")
    op.execute("ALTER TABLE textbook_entries DROP COLUMN example_lemmas")
