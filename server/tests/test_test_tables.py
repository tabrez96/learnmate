from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from learnmate.clock import FakeClock
from learnmate.db import create_db_engine
from learnmate.models import (
    BUDGET_LEVELS,
    GRADE_BANDS,
    LLM_PURPOSES,
    OUTBOX_STATUSES,
    POINTS_REASONS,
    TEST_KINDS,
    TEST_STATUSES,
    BudgetAlert,
    Chunk,
    LlmUsage,
    Material,
    Outbox,
    Points,
    Question,
    StudySession,
    StudyTest,
)

TEST_TABLES = {"test", "question", "points", "outbox", "llm_usage", "budget_alert"}
SESSION_TABLES = {
    "session",
    "session_material",
    "session_chapter",
    "session_event",
    "heartbeat",
    "message",
}


def _test(study: StudySession, value: Any, column: str) -> StudyTest:
    return StudyTest(
        **{
            "session_id": study.id,
            "subject_id": study.subject_id,
            "kind": "daily",
            "graded": True,
            column: value,
        }
    )


def _points(study: StudySession, value: Any, _: str) -> Points:
    return Points(session_id=study.id, reason=value, amount=10)


def _outbox(_: StudySession, value: Any, __: str) -> Outbox:
    return Outbox(text="hi", status=value)


def _usage(_: StudySession, value: Any, __: str) -> LlmUsage:
    return LlmUsage(model="m", purpose=value, cost_usd=Decimal("0.001"))


def _alert(_: StudySession, value: Any, __: str) -> BudgetAlert:
    return BudgetAlert(month="2026-01", level=value)


ENUMS: list[
    tuple[Callable[[StudySession, Any, str], Any], str, tuple[Any, ...], Any]
] = [
    (_test, "kind", TEST_KINDS, "bogus"),
    (_test, "status", TEST_STATUSES, "bogus"),
    (_test, "band", GRADE_BANDS, "Z"),
    (_points, "reason", POINTS_REASONS, "bogus"),
    (_outbox, "status", OUTBOX_STATUSES, "bogus"),
    (_usage, "purpose", LLM_PURPOSES, "bogus"),
    (_alert, "level", BUDGET_LEVELS, 50),
]
ENUM_IDS = [
    "test.kind",
    "test.status",
    "test.band",
    "points.reason",
    "outbox.status",
    "llm_usage.purpose",
    "budget_alert.level",
]


def _study_test(study: StudySession, **kwargs: Any) -> StudyTest:
    return StudyTest(
        session_id=study.id,
        subject_id=study.subject_id,
        kind=kwargs.pop("kind", "daily"),
        graded=kwargs.pop("graded", True),
        **kwargs,
    )


def test_upgrade_creates_test_tables(engine: Engine) -> None:
    assert TEST_TABLES <= set(inspect(engine).get_table_names())


def test_downgrade_removes_test_tables(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "-1")
    eng = create_db_engine(alembic_config.get_main_option("sqlalchemy.url"))
    try:
        tables = set(inspect(eng).get_table_names())
    finally:
        eng.dispose()
    assert not TEST_TABLES & tables
    assert SESSION_TABLES <= tables


@pytest.mark.parametrize(("make", "column", "values", "bogus"), ENUMS, ids=ENUM_IDS)
def test_enum_values(
    db: Session,
    study_session: StudySession,
    make: Callable[[StudySession, Any, str], Any],
    column: str,
    values: tuple[Any, ...],
    bogus: Any,
) -> None:
    db.add_all([make(study_session, value, column) for value in values])
    db.commit()
    db.add(make(study_session, bogus, column))
    with pytest.raises(IntegrityError):
        db.commit()


def test_ungraded_challenge_and_bonus(db: Session, study_session: StudySession) -> None:
    db.add_all(
        [
            _study_test(study_session, kind="challenge", graded=False),
            _study_test(study_session, kind="bonus", graded=False),
        ]
    )
    db.commit()
    rows = db.query(StudyTest).all()
    assert {r.kind for r in rows} == {"challenge", "bonus"}
    for row in rows:
        assert row.graded is False
        assert row.status == "in_progress"
        assert row.band is None


def test_subject_delete_keeps_tests(db: Session, study_session: StudySession) -> None:
    study_test = _study_test(study_session)
    db.add(study_test)
    db.flush()
    db.add(
        Question(
            test_id=study_test.id,
            position=0,
            prompt="Q?",
            options_json="[]",
            correct_index=0,
        )
    )
    db.commit()
    db.execute(text("DELETE FROM subject"))
    db.commit()
    row = db.execute(text("SELECT subject_id FROM test")).one()
    assert row.subject_id is None
    assert db.execute(text("SELECT COUNT(*) FROM question")).scalar_one() == 1


def test_session_delete_keeps_tests(db: Session, study_session: StudySession) -> None:
    db.add_all(
        [
            _study_test(study_session),
            Points(session_id=study_session.id, reason="test", amount=5),
        ]
    )
    db.commit()
    db.execute(text("DELETE FROM session"))
    db.commit()
    row = db.execute(text("SELECT session_id FROM test")).one()
    assert row.session_id is None
    assert db.execute(text("SELECT COUNT(*) FROM points")).scalar_one() == 0


def test_test_delete_cascades_questions(
    db: Session, study_session: StudySession
) -> None:
    study_test = _study_test(study_session)
    db.add(study_test)
    db.flush()
    db.add(
        Question(
            test_id=study_test.id,
            position=0,
            prompt="Q?",
            options_json="[]",
            correct_index=0,
        )
    )
    db.commit()
    db.execute(text("DELETE FROM test"))
    db.commit()
    assert db.execute(text("SELECT COUNT(*) FROM question")).scalar_one() == 0


def test_chunk_delete_keeps_question(db: Session, study_session: StudySession) -> None:
    material = Material(subject_id=study_session.subject_id, title="N", kind="upload")
    db.add(material)
    db.flush()
    chunk = Chunk(material_id=material.id, position=0, text="x")
    study_test = _study_test(study_session)
    db.add_all([chunk, study_test])
    db.flush()
    db.add(
        Question(
            test_id=study_test.id,
            position=0,
            prompt="Q?",
            options_json="[]",
            correct_index=0,
            chunk_id=chunk.id,
        )
    )
    db.commit()
    db.execute(text("DELETE FROM chunk"))
    db.commit()
    row = db.execute(text("SELECT chunk_id FROM question")).one()
    assert row.chunk_id is None


def test_budget_alert_unique(db: Session) -> None:
    db.add_all(
        [
            BudgetAlert(month="2026-01", level=80),
            BudgetAlert(month="2026-01", level=100),
            BudgetAlert(month="2026-02", level=80),
        ]
    )
    db.commit()
    db.add(BudgetAlert(month="2026-01", level=80))
    with pytest.raises(IntegrityError):
        db.commit()


def test_clock_fills_timestamps(
    db: Session, study_session: StudySession, clock: FakeClock
) -> None:
    points = Points(session_id=study_session.id, reason="test", amount=5)
    usage = LlmUsage(model="m", purpose="lesson", cost_usd=Decimal("0.012345"))
    study_test = _study_test(study_session)
    db.add_all([points, usage, study_test])
    db.commit()
    assert points.at == clock.now()
    assert usage.at == clock.now()
    assert study_test.created_at == clock.now()
    db.refresh(usage)
    assert usage.cost_usd == Decimal("0.012345")


def test_defaults(db: Session) -> None:
    outbox = Outbox(text="hi")
    db.add(outbox)
    db.commit()
    db.refresh(outbox)
    assert outbox.status == "pending"
    assert outbox.attempts == 0
