from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamp


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("kanji", "kana", name="uq_words_kanji_kana"),
        Index("ix_words_kanji_prefix", "kanji", postgresql_ops={"kanji": "text_pattern_ops"}),
        Index(
            "ix_words_kana_prefix", "kana_norm", postgresql_ops={"kana_norm": "text_pattern_ops"}
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    jmdict_id: Mapped[str | None]
    kanji: Mapped[str] = mapped_column(default="")
    kana: Mapped[str]
    kana_norm: Mapped[str]
    romaji: Mapped[str]
    hanviet: Mapped[str] = mapped_column(default="")
    pos: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    jlpt_level: Mapped[str | None] = mapped_column(String(2))
    embedding = mapped_column(Vector(384), nullable=True)


class WordSense(Base):
    __tablename__ = "word_senses"
    __table_args__ = (
        Index(
            "ix_senses_gloss_trgm",
            "gloss",
            postgresql_using="gin",
            postgresql_ops={"gloss": "gin_trgm_ops"},
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), index=True)
    lang: Mapped[str]
    gloss: Mapped[str]
    order: Mapped[int] = mapped_column(default=0)


Index(
    "ix_senses_gloss_prefix",
    func.lower(WordSense.gloss).label("gloss_lower"),
    postgresql_ops={"gloss_lower": "text_pattern_ops"},
)


class Kanji(Base):
    __tablename__ = "kanji"
    char: Mapped[str] = mapped_column(String(1), primary_key=True)
    hanviet: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    meaning: Mapped[str] = mapped_column(default="")
    strokes: Mapped[int | None]
    jlpt_level: Mapped[str | None] = mapped_column(String(2))


class WordEdit(Timestamp, Base):
    __tablename__ = "word_edits"
    __table_args__ = (Index("ix_word_edits_word_id", "word_id", "id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    field: Mapped[str]
    old: Mapped[str]
    new: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
