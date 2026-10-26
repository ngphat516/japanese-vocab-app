from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamp


class SearchHistory(Base):
    __tablename__ = "search_history"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_history_user_word"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    query: Mapped[str] = mapped_column(Text, default="")
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SavedWord(Timestamp, Base):
    __tablename__ = "saved_words"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_saved_user_word"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    note: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


class Collection(Timestamp, Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collection_user_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)


class CollectionWord(Base):
    __tablename__ = "collection_words"
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    saved_word_id: Mapped[int] = mapped_column(
        ForeignKey("saved_words.id", ondelete="CASCADE"), primary_key=True
    )


Index(
    "ix_history_user_searched",
    SearchHistory.user_id,
    SearchHistory.searched_at.desc(),
    SearchHistory.id.desc(),
)
Index("ix_saved_user_created", SavedWord.user_id, SavedWord.created_at.desc(), SavedWord.id.desc())
Index("ix_collection_words_saved", CollectionWord.saved_word_id)
