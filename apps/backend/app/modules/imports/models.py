from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamp


class ImportJob(Timestamp, Base):
    __tablename__ = "import_jobs"
    __mapper_args__: ClassVar[dict] = {"eager_defaults": True}
    __table_args__ = (Index("ix_import_jobs_status_updated", "status", "updated_at"),)
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
    payload: Mapped[bytes | None] = mapped_column(LargeBinary)
    processed: Mapped[int] = mapped_column(default=0, server_default="0")
    auto_furigana: Mapped[bool] = mapped_column(default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.clock_timestamp()
    )


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
