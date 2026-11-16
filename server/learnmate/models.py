"""Content tables. `chunk_fts` (FTS5) is not a model: the migration creates it and its triggers keep it in sync."""

import datetime as dt
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _cascade_fk(target: str, *, index: bool = True) -> Any:
    return mapped_column(ForeignKey(target, ondelete="CASCADE"), index=index)


def _created_at() -> Mapped[dt.datetime]:
    return mapped_column(DateTime, server_default=func.current_timestamp())


class Family(Base):
    __tablename__ = "family"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_name: Mapped[str] = mapped_column(String(100))
    grade: Mapped[int]
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_link_code: Mapped[str | None] = mapped_column(String(32))
    fallback_hash: Mapped[str | None] = mapped_column(String(255))
    fallback_wrong: Mapped[int] = mapped_column(server_default="0")
    fallback_locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime)
    outside_books_allowed: Mapped[bool] = mapped_column(server_default=true())
    inactivity_warn_s: Mapped[int] = mapped_column(server_default="240")
    inactivity_lock_s: Mapped[int] = mapped_column(server_default="300")
    created_at: Mapped[dt.datetime] = _created_at()


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[dt.datetime] = _created_at()


class Material(Base):
    __tablename__ = "material"
    __table_args__ = (
        CheckConstraint("kind IN ('upload', 'classroom')", name="ck_material_kind"),
        CheckConstraint(
            "status IN ('reading', 'ready', 'failed')", name="ck_material_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = _cascade_fk("subject.id")
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))
    source_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), server_default="reading")
    error: Mapped[str | None] = mapped_column(Text)
    pages_total: Mapped[int | None]
    pages_read: Mapped[int] = mapped_column(server_default="0")
    chapters_hint: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _created_at()


class MaterialFile(Base):
    __tablename__ = "material_file"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = _cascade_fk("material.id")
    path: Mapped[str] = mapped_column(Text)
    mime: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]


class Chapter(Base):
    __tablename__ = "chapter"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = _cascade_fk("material.id")
    name: Mapped[str] = mapped_column(String(200))
    position: Mapped[int]


class Figure(Base):
    __tablename__ = "figure"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = _cascade_fk("material.id")
    chapter_id: Mapped[int | None] = _cascade_fk("chapter.id")
    page: Mapped[int | None]
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (
        CheckConstraint("kind IN ('text', 'figure')", name="ck_chunk_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = _cascade_fk("material.id")
    # Null when no chapters were detected.
    chapter_id: Mapped[int | None] = _cascade_fk("chapter.id")
    page: Mapped[int | None]
    position: Mapped[int]
    kind: Mapped[str] = mapped_column(String(16), server_default="text")
    figure_id: Mapped[int | None] = _cascade_fk("figure.id", index=False)
    text: Mapped[str] = mapped_column(Text)
    # 384 float32 values, normalised; null until embedded.
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    # Which model produced the embedding; stale rows get re-embedded.
    embed_model: Mapped[str | None] = mapped_column(String(100))


class Exam(Base):
    __tablename__ = "exam"
    __table_args__ = (
        UniqueConstraint("subject_id", "date", name="uq_exam_subject_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = _cascade_fk("subject.id")
    date: Mapped[dt.date] = mapped_column(Date)
