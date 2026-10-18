from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamp


class Textbook(Timestamp, Base):
    __tablename__ = "textbooks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    publisher: Mapped[str | None]
    level: Mapped[str | None]
    edition: Mapped[str | None]
    visibility: Mapped[str] = mapped_column(default="private")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    license: Mapped[str | None]
    source_url: Mapped[str | None]


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("textbook_id", "number", name="uq_lesson_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id", ondelete="CASCADE"))
    number: Mapped[int]
    title: Mapped[str]


class Entry(Timestamp, Base):
    __tablename__ = "textbook_entries"
    __table_args__ = (
        UniqueConstraint("word_id", "lesson_id", name="uq_entry_word_lesson"),
        Index("ix_entries_lesson_order", "lesson_id", "order_no"),
        Index(
            "ix_entries_search_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    order_no: Mapped[int]
    content: Mapped[list] = mapped_column(JSONB)
    search_text: Mapped[str]
