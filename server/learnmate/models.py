"""Content tables. `chunk_fts` (FTS5) is not a model: the migration creates it and its triggers keep it in sync."""

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _cascade_fk(target: str, *, index: bool = True) -> Any:
    return mapped_column(ForeignKey(target, ondelete="CASCADE"), index=index)


def _cascade_pk(target: str) -> Any:
    return mapped_column(ForeignKey(target, ondelete="CASCADE"), primary_key=True)


def _clock_stamp() -> Mapped[dt.datetime]:
    # Filled from the injected clock on insert (see db.py); the server default
    # is the fallback for raw SQL.
    return mapped_column(
        DateTime, server_default=func.current_timestamp(), info={"clock": True}
    )


SESSION_TYPES = ("learn", "recap", "test_only")
SESSION_STATES = ("set_up", "running", "locked", "ended", "force_ended", "cancelled")
END_REASONS = ("pin", "fallback")
SESSION_EVENT_TYPES = (
    "started",
    "left",
    "back",
    "heartbeat_lost",
    "warned",
    "locked",
    "unlocked",
    "wrong_pin",
    "pin_locked",
    "pin_resent",
    "pin_replaced",
    "fallback_wrong",
    "ended",
)
MESSAGE_ROLES = ("mentor", "student")
TEST_KINDS = (
    "warmup",
    "daily",
    "weekly",
    "surprise",
    "test_only",
    "challenge",
    "bonus",
)
TEST_STATUSES = ("in_progress", "done", "missed")
GRADE_BANDS = ("A", "B", "C", "D", "E", "F")
POINTS_REASONS = ("warmup", "quick_check", "test", "challenge", "bonus", "streak")
OUTBOX_STATUSES = ("pending", "sent")
LLM_PURPOSES = (
    "read_page",
    "chapters",
    "rewrite",
    "lesson",
    "answer",
    "outside",
    "questions",
    "figures",
)
BUDGET_LEVELS = (80, 100)


def _one_of(column: str, values: tuple[str, ...], name: str) -> CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=name)


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
    created_at: Mapped[dt.datetime] = _clock_stamp()


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[dt.datetime] = _clock_stamp()


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
    created_at: Mapped[dt.datetime] = _clock_stamp()


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


class MaterialPage(Base):
    __tablename__ = "material_page"
    __table_args__ = (
        UniqueConstraint("material_id", "page", name="uq_material_page_material_page"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = _cascade_fk("material.id")
    # Set once chapters are detected; null until then.
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapter.id", ondelete="SET NULL"), index=True
    )
    # 1-based across all files of the material, in upload order.
    page: Mapped[int]
    text: Mapped[str] = mapped_column(Text)


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


class StudySession(Base):
    __tablename__ = "session"
    __table_args__ = (
        _one_of("type", SESSION_TYPES, "ck_session_type"),
        _one_of("state", SESSION_STATES, "ck_session_state"),
        _one_of("end_reason", END_REASONS, "ck_session_end_reason"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # SET NULL: deleting a subject keeps its sessions, tests and grades.
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subject.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[str] = mapped_column(String(16))
    question_count: Mapped[int]
    state: Mapped[str] = mapped_column(String(16), server_default="set_up")
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    # Encrypted with the server's PIN key, for "Forgot the PIN".
    pin_enc: Mapped[str | None] = mapped_column(Text)
    pin_version: Mapped[int] = mapped_column(server_default="1")
    pin_last_sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    wrong_pins: Mapped[int] = mapped_column(server_default="0")
    pin_locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = _clock_stamp()
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    end_reason: Mapped[str | None] = mapped_column(String(16))
    study_seconds: Mapped[int] = mapped_column(server_default="0")
    # Plan steps and their status.
    plan_json: Mapped[str | None] = mapped_column(Text)


class SessionMaterial(Base):
    __tablename__ = "session_material"

    session_id: Mapped[int] = _cascade_pk("session.id")
    material_id: Mapped[int] = _cascade_pk("material.id")


class SessionChapter(Base):
    __tablename__ = "session_chapter"

    session_id: Mapped[int] = _cascade_pk("session.id")
    chapter_id: Mapped[int] = _cascade_pk("chapter.id")


class SessionEvent(Base):
    __tablename__ = "session_event"
    __table_args__ = (_one_of("type", SESSION_EVENT_TYPES, "ck_session_event_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = _cascade_fk("session.id")
    type: Mapped[str] = mapped_column(String(16))
    at: Mapped[dt.datetime] = _clock_stamp()
    data_json: Mapped[str | None] = mapped_column(Text)


class Heartbeat(Base):
    __tablename__ = "heartbeat"

    session_id: Mapped[int] = _cascade_pk("session.id")
    last_at: Mapped[dt.datetime] = _clock_stamp()


class Message(Base):
    __tablename__ = "message"
    __table_args__ = (_one_of("role", MESSAGE_ROLES, "ck_message_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = _cascade_fk("session.id")
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    # Chunk ids, material title, chapter, page.
    sources_json: Mapped[str | None] = mapped_column(Text)
    visual_json: Mapped[str | None] = mapped_column(Text)
    outside: Mapped[bool] = mapped_column(server_default=false())
    outside_source_url: Mapped[str | None] = mapped_column(Text)
    # Query used, chunk ids and scores, rerank on or off; for spot checks.
    retrieval_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _clock_stamp()


class StudyTest(Base):
    __tablename__ = "test"
    __table_args__ = (
        _one_of("kind", TEST_KINDS, "ck_test_kind"),
        _one_of("status", TEST_STATUSES, "ck_test_status"),
        _one_of("band", GRADE_BANDS, "ck_test_band"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # SET NULL: tests and grades outlive their session and subject.
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("session.id", ondelete="SET NULL"), index=True
    )
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subject.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), server_default="in_progress")
    # False for warm-up, challenge and bonus.
    graded: Mapped[bool]
    current_index: Mapped[int] = mapped_column(server_default="0")
    score_pct: Mapped[int | None]
    # Null until graded.
    band: Mapped[str | None] = mapped_column(String(1))
    created_at: Mapped[dt.datetime] = _clock_stamp()
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = _cascade_fk("test.id")
    position: Mapped[int]
    prompt: Mapped[str] = mapped_column(Text)
    # Four options.
    options_json: Mapped[str] = mapped_column(Text)
    correct_index: Mapped[int]
    explanation: Mapped[str | None] = mapped_column(Text)
    chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("chunk.id", ondelete="SET NULL"), index=True
    )
    answer_index: Mapped[int | None]
    answered_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class Points(Base):
    __tablename__ = "points"
    __table_args__ = (_one_of("reason", POINTS_REASONS, "ck_points_reason"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = _cascade_fk("session.id")
    reason: Mapped[str] = mapped_column(String(16))
    amount: Mapped[int]
    at: Mapped[dt.datetime] = _clock_stamp()


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = (_one_of("status", OUTBOX_STATUSES, "ck_outbox_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    buttons_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    attempts: Mapped[int] = mapped_column(server_default="0")
    # Null means send now.
    next_try_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class LlmUsage(Base):
    __tablename__ = "llm_usage"
    __table_args__ = (_one_of("purpose", LLM_PURPOSES, "ck_llm_usage_purpose"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[dt.datetime] = _clock_stamp()
    model: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(String(16))
    input_tokens: Mapped[int] = mapped_column(server_default="0")
    output_tokens: Mapped[int] = mapped_column(server_default="0")
    web_searches: Mapped[int] = mapped_column(server_default="0")
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6))


class BudgetAlert(Base):
    __tablename__ = "budget_alert"
    __table_args__ = (
        CheckConstraint("level IN (80, 100)", name="ck_budget_alert_level"),
        UniqueConstraint("month", "level", name="uq_budget_alert_month_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # YYYY-MM
    month: Mapped[str] = mapped_column(String(7))
    level: Mapped[int]
