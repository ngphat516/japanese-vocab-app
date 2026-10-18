"""Initial P0 schema, PostgreSQL 16 with pg_trgm and pgvector."""

from alembic import op

revision = "0001_p0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "CREATE TABLE kanji (\n\tchar VARCHAR(1) NOT NULL, \n\thanviet VARCHAR[] NOT NULL, \n\tmeaning VARCHAR NOT NULL, \n\tstrokes INTEGER, \n\tjlpt_level VARCHAR(2), \n\tPRIMARY KEY (char)\n)"
    )
    op.execute(
        'CREATE TABLE rate_buckets (\n\tkey VARCHAR(300) NOT NULL, \n\t"window" INTEGER NOT NULL, \n\tcount INTEGER NOT NULL, \n\tPRIMARY KEY (key)\n)'
    )
    op.execute(
        "CREATE TABLE users (\n\tid SERIAL NOT NULL, \n\temail VARCHAR(320) NOT NULL, \n\tpassword_hash VARCHAR NOT NULL, \n\tdisplay_name VARCHAR NOT NULL, \n\trole VARCHAR(10) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (email)\n)"
    )
    op.execute(
        "CREATE TABLE words (\n\tid SERIAL NOT NULL, \n\tjmdict_id VARCHAR, \n\tkanji VARCHAR NOT NULL, \n\tkana VARCHAR NOT NULL, \n\tkana_norm VARCHAR NOT NULL, \n\tromaji VARCHAR NOT NULL, \n\thanviet VARCHAR NOT NULL, \n\tpos VARCHAR[] NOT NULL, \n\tjlpt_level VARCHAR(2), \n\tembedding VECTOR(384), \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_words_kanji_kana UNIQUE (kanji, kana)\n)"
    )
    op.execute("CREATE INDEX ix_words_kana_prefix ON words (kana_norm text_pattern_ops)")
    op.execute("CREATE INDEX ix_words_kanji_prefix ON words (kanji text_pattern_ops)")
    op.execute(
        "CREATE TABLE refresh_tokens (\n\tdigest VARCHAR(64) NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked BOOLEAN NOT NULL, \n\tPRIMARY KEY (digest), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id)")
    op.execute(
        "CREATE TABLE textbooks (\n\tid SERIAL NOT NULL, \n\tname VARCHAR NOT NULL, \n\tpublisher VARCHAR, \n\tlevel VARCHAR, \n\tedition VARCHAR, \n\tvisibility VARCHAR NOT NULL, \n\towner_id INTEGER NOT NULL, \n\tlicense VARCHAR, \n\tsource_url VARCHAR, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(owner_id) REFERENCES users (id)\n)"
    )
    op.execute("CREATE INDEX ix_textbooks_owner_id ON textbooks (owner_id)")
    op.execute(
        'CREATE TABLE word_senses (\n\tid SERIAL NOT NULL, \n\tword_id INTEGER NOT NULL, \n\tlang VARCHAR NOT NULL, \n\tgloss VARCHAR NOT NULL, \n\t"order" INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(word_id) REFERENCES words (id) ON DELETE CASCADE\n)'
    )
    op.execute("CREATE INDEX ix_senses_gloss_trgm ON word_senses USING gin (gloss gin_trgm_ops)")
    op.execute("CREATE INDEX ix_word_senses_word_id ON word_senses (word_id)")
    op.execute(
        "CREATE TABLE import_jobs (\n\tid SERIAL NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\ttextbook_id INTEGER NOT NULL, \n\tadapter VARCHAR NOT NULL, \n\tfile_key VARCHAR NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\ttotal INTEGER NOT NULL, \n\tmatched INTEGER NOT NULL, \n\tambiguous INTEGER NOT NULL, \n\tfailed INTEGER NOT NULL, \n\terror VARCHAR, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(textbook_id) REFERENCES textbooks (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE lessons (\n\tid SERIAL NOT NULL, \n\ttextbook_id INTEGER NOT NULL, \n\tnumber INTEGER NOT NULL, \n\ttitle VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_lesson_number UNIQUE (textbook_id, number), \n\tFOREIGN KEY(textbook_id) REFERENCES textbooks (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE import_rows (\n\tid SERIAL NOT NULL, \n\tjob_id INTEGER NOT NULL, \n\trow_no INTEGER NOT NULL, \n\traw JSONB NOT NULL, \n\tkanji VARCHAR NOT NULL, \n\tkana VARCHAR NOT NULL, \n\tlesson_no INTEGER NOT NULL, \n\torder_no INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tmatch_status VARCHAR NOT NULL, \n\tcandidate_word_ids INTEGER[] NOT NULL, \n\tchosen_word_id INTEGER, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(job_id) REFERENCES import_jobs (id) ON DELETE CASCADE, \n\tFOREIGN KEY(chosen_word_id) REFERENCES words (id)\n)"
    )
    op.execute("CREATE INDEX ix_import_rows_job_id ON import_rows (job_id)")
    op.execute(
        "CREATE TABLE textbook_entries (\n\tid SERIAL NOT NULL, \n\tword_id INTEGER NOT NULL, \n\tlesson_id INTEGER NOT NULL, \n\torder_no INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tsearch_text VARCHAR NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_entry_word_lesson UNIQUE (word_id, lesson_id), \n\tFOREIGN KEY(word_id) REFERENCES words (id), \n\tFOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_entries_lesson_order ON textbook_entries (lesson_id, order_no)")
    op.execute(
        "CREATE INDEX ix_entries_search_trgm ON textbook_entries USING gin (search_text gin_trgm_ops)"
    )
    op.execute("CREATE INDEX ix_textbook_entries_word_id ON textbook_entries (word_id)")


def downgrade():
    op.drop_table("textbook_entries")
    op.drop_table("import_rows")
    op.drop_table("lessons")
    op.drop_table("import_jobs")
    op.drop_table("word_senses")
    op.drop_table("textbooks")
    op.drop_table("refresh_tokens")
    op.drop_table("words")
    op.drop_table("users")
    op.drop_table("rate_buckets")
    op.drop_table("kanji")
