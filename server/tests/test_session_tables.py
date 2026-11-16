from collections.abc import Callable
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from learnmate.db import create_db_engine
from learnmate.models import (
    END_REASONS,
    MESSAGE_ROLES,
    SESSION_EVENT_TYPES,
    SESSION_STATES,
    SESSION_TYPES,
    Chapter,
    Heartbeat,
    Material,
    Message,
    SessionChapter,
    SessionEvent,
    SessionMaterial,
    StudySession,
)

SESSION_TABLES = {
    "session",
    "session_material",
    "session_chapter",
    "session_event",
    "heartbeat",
    "message",
}
CONTENT_TABLES = {"subject", "material", "chapter", "chunk", "exam", "family"}


def _session(_: StudySession, value: str, column: str) -> StudySession:
    return StudySession(**{"type": "learn", "question_count": 5, column: value})


def _event(study: StudySession, value: str, _: str) -> SessionEvent:
    return SessionEvent(session_id=study.id, type=value)


def _message(study: StudySession, value: str, _: str) -> Message:
    return Message(session_id=study.id, role=value, text="hi")


ENUMS: list[tuple[Callable[[StudySession, str, str], Any], str, tuple[str, ...]]] = [
    (_session, "type", SESSION_TYPES),
    (_session, "state", SESSION_STATES),
    (_session, "end_reason", END_REASONS),
    (_event, "type", SESSION_EVENT_TYPES),
    (_message, "role", MESSAGE_ROLES),
]
ENUM_IDS = ["session.type", "session.state", "session.end_reason", "event", "message"]


def test_upgrade_creates_session_tables(engine: Engine) -> None:
    assert SESSION_TABLES <= set(inspect(engine).get_table_names())


def test_downgrade_removes_session_tables(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "-1")
    eng = create_db_engine(alembic_config.get_main_option("sqlalchemy.url"))
    try:
        tables = set(inspect(eng).get_table_names())
    finally:
        eng.dispose()
    assert not SESSION_TABLES & tables
    assert CONTENT_TABLES <= tables


@pytest.mark.parametrize(("make", "column", "values"), ENUMS, ids=ENUM_IDS)
def test_enum_values(
    db: Session,
    study_session: StudySession,
    make: Callable[[StudySession, str, str], Any],
    column: str,
    values: tuple[str, ...],
) -> None:
    db.add_all([make(study_session, value, column) for value in values])
    db.commit()
    db.add(make(study_session, "bogus", column))
    with pytest.raises(IntegrityError):
        db.commit()


def test_session_delete_cascades(db: Session, study_session: StudySession) -> None:
    material = Material(subject_id=study_session.subject_id, title="N", kind="upload")
    db.add(material)
    db.flush()
    chapter = Chapter(material_id=material.id, name="One", position=0)
    db.add(chapter)
    db.flush()
    sid = study_session.id
    db.add_all(
        [
            SessionMaterial(session_id=sid, material_id=material.id),
            SessionChapter(session_id=sid, chapter_id=chapter.id),
            SessionEvent(session_id=sid, type="started"),
            Heartbeat(session_id=sid),
            Message(session_id=sid, role="mentor", text="hi"),
        ]
    )
    db.commit()
    db.execute(text("DELETE FROM session"))
    db.commit()
    for table in SESSION_TABLES - {"session"}:
        assert db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 0


def test_subject_delete_keeps_session(db: Session, study_session: StudySession) -> None:
    db.commit()
    db.execute(text("DELETE FROM subject"))
    db.commit()
    row = db.execute(text("SELECT subject_id FROM session")).one()
    assert row.subject_id is None
