import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from learnmate.clock import FakeClock, SystemClock
from learnmate.models import SessionEvent, StudySession, Subject

START = dt.datetime(2026, 1, 5, 9, 0)


def test_fake_clock_advances() -> None:
    fake = FakeClock(START)
    assert fake.now() == START
    fake.advance(seconds=90)
    assert fake.now() == START + dt.timedelta(seconds=90)


def test_system_clock_is_naive_utc() -> None:
    now = SystemClock().now()
    expected = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    assert now.tzinfo is None
    assert abs(now - expected) < dt.timedelta(seconds=5)


def test_clock_sets_created_at_and_event_at(
    db: Session, clock: FakeClock, study_session: StudySession
) -> None:
    event = SessionEvent(session_id=study_session.id, type="started")
    db.add(event)
    db.commit()
    subject = db.get(Subject, study_session.subject_id)
    assert subject.created_at == study_session.created_at == event.at == clock.now()


def test_advancing_clock_changes_next_row(db: Session, clock: FakeClock) -> None:
    first = Subject(name="Maths", icon="calc")
    db.add(first)
    db.commit()
    clock.advance(seconds=60)
    second = Subject(name="Science", icon="flask")
    db.add(second)
    db.commit()
    assert second.created_at - first.created_at == dt.timedelta(seconds=60)


def test_explicit_timestamp_is_kept(db: Session, study_session: StudySession) -> None:
    explicit = dt.datetime(2025, 3, 1, 8, 0)
    event = SessionEvent(session_id=study_session.id, type="started", at=explicit)
    db.add(event)
    db.commit()
    db.expire_all()
    assert db.get(SessionEvent, event.id).at == explicit


def test_raw_insert_falls_back_to_server_default(db: Session) -> None:
    db.execute(text("INSERT INTO subject (name, icon) VALUES ('Maths', 'calc')"))
    db.commit()
    assert db.execute(text("SELECT created_at FROM subject")).scalar_one() is not None


def test_app_exposes_system_clock(client: TestClient) -> None:
    assert isinstance(client.app.state.clock, SystemClock)
