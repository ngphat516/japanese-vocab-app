from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamp


class ImportJob(Timestamp, Base):
    __tablename__ = "import_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id", ondelete="CASCADE"))
    adapter: Mapped[str]
    file_key: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending")
    total: Mapped[int] = mapped_column(default=0)
    matched: Mapped[int] = mapped_column(default=0)
    ambiguous: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None]


class ImportRow(Base):
    __tablename__ = "import_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True
    )
    row_no: Mapped[int]
    raw: Mapped[dict] = mapped_column(JSONB)
    kanji: Mapped[str]
    kana: Mapped[str]
    lesson_no: Mapped[int]
    order_no: Mapped[int]
    content: Mapped[list] = mapped_column(JSONB)
    match_status: Mapped[str]
    candidate_word_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    chosen_word_id: Mapped[int | None] = mapped_column(ForeignKey("words.id"))
