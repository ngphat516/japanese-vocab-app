"""User-owned history, saved words and collections."""

from alembic import op

revision = "0005_notebook"
down_revision = "0004_example_lemmas"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE search_history (
        id SERIAL PRIMARY KEY, user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        word_id integer NOT NULL REFERENCES words(id) ON DELETE CASCADE,
        query text NOT NULL DEFAULT '', searched_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_history_user_word UNIQUE(user_id, word_id))""")
    op.execute(
        "CREATE INDEX ix_history_user_searched ON search_history(user_id, searched_at DESC, id DESC)"
    )
    op.execute("""CREATE TABLE saved_words (
        id SERIAL PRIMARY KEY, user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        word_id integer NOT NULL REFERENCES words(id) ON DELETE CASCADE, note text NOT NULL DEFAULT '',
        tags text[] NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_saved_user_word UNIQUE(user_id, word_id))""")
    op.execute(
        "CREATE INDEX ix_saved_user_created ON saved_words(user_id, created_at DESC, id DESC)"
    )
    op.execute("""CREATE TABLE collections (
        id SERIAL PRIMARY KEY, user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_collection_user_name UNIQUE(user_id, name))""")
    op.execute("""CREATE TABLE collection_words (
        collection_id integer NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
        saved_word_id integer NOT NULL REFERENCES saved_words(id) ON DELETE CASCADE,
        PRIMARY KEY(collection_id, saved_word_id))""")
    op.execute("CREATE INDEX ix_collection_words_saved ON collection_words(saved_word_id)")


def downgrade():
    for table in ["collection_words", "collections", "saved_words", "search_history"]:
        op.drop_table(table)
