"""Import payload/progress and pinned Procrastinate 3.10 schema."""

from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "0010_import_worker"
down_revision = "0009_hanviet_sources"
branch_labels = depends_on = None


def upgrade():
    op.add_column("import_jobs", sa.Column("payload", sa.LargeBinary(), nullable=True))
    op.add_column(
        "import_jobs", sa.Column("processed", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "import_jobs",
        sa.Column("auto_furigana", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "import_jobs",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_import_jobs_status_updated", "import_jobs", ["status", "updated_at"])
    op.execute("CREATE SCHEMA procrastinate")
    op.execute("SET LOCAL search_path = procrastinate, public")
    schema = Path(__file__).with_name("0010_procrastinate_3_10.sql").read_text(encoding="utf-8")
    op.get_bind().connection.dbapi_connection.run_async(
        lambda connection: connection.execute(schema)
    )
    op.execute("""DO $$ DECLARE fn regprocedure; BEGIN
        FOR fn IN SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='procrastinate'
        LOOP EXECUTE format('ALTER FUNCTION %s SET search_path = procrastinate, public', fn); END LOOP;
        END $$""")
    op.execute("SET LOCAL search_path = public")


def downgrade():
    op.execute("DROP SCHEMA procrastinate CASCADE")
    op.drop_index("ix_import_jobs_status_updated", table_name="import_jobs")
    for name in ["updated_at", "auto_furigana", "processed", "payload"]:
        op.drop_column("import_jobs", name)
