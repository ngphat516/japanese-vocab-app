from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
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
    version: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    content_furigana: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))
    auto_furigana: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    search_text: Mapped[str]
    lemmas: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'"), default=list
    )
    example_lemmas: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'"), default=list
    )


Index(
    "ix_entries_search_prefix",
    func.lower(Entry.search_text).label("search_lower"),
    postgresql_ops={"search_lower": "text_pattern_ops"},
)

Index("ix_entries_lemmas", Entry.lemmas, postgresql_using="gin")
Index("ix_entries_example_lemmas", Entry.example_lemmas, postgresql_using="gin")
