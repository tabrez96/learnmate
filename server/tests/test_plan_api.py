import datetime as dt

from fastapi.testclient import TestClient

from learnmate.clock import FakeClock
from learnmate.models import (
    Chapter,
    Exam,
    Material,
    Points,
    SessionChapter,
    StudySession,
    StudyTest,
    Subject,
)

API = "/api/v1"
MON = dt.datetime(2026, 1, 5, 9, 0)


def _subject(client: TestClient) -> int:
    with client.app.state.session_factory() as db:
        subject = Subject(name="Science", icon="flask")
        db.add(subject)
        db.commit()
        return subject.id


def _session(
    client: TestClient,
    subject_id: int,
    *,
    state: str = "running",
    started_at: dt.datetime | None = MON,
    type: str = "learn",
) -> int:
    with client.app.state.session_factory() as db:
        row = StudySession(
            subject_id=subject_id,
            type=type,
            question_count=5,
            state=state,
            started_at=started_at,
        )
        db.add(row)
        db.commit()
        return row.id


def _plan(client: TestClient, session_id: int) -> dict:
    r = client.get(f"{API}/sessions/{session_id}/plan")
    assert r.status_code == 200
    return r.json()


def test_get_plan_builds_once_and_stays_stable(client: TestClient) -> None:
    client.app.state.clock = FakeClock(MON)
    subject_id = _subject(client)
    session_id = _session(client, subject_id)
    first = _plan(client, session_id)
    assert first["current_step"] == "warmup"
    with client.app.state.session_factory() as db:
        db.add(Exam(subject_id=subject_id, date=dt.date(2026, 1, 7)))
        db.commit()
    assert _plan(client, session_id) == first


def test_plan_topic_from_chapters(client: TestClient) -> None:
    subject_id = _subject(client)
    session_id = _session(client, subject_id, type="recap")
    with client.app.state.session_factory() as db:
        material = Material(subject_id=subject_id, title="Plants", kind="upload")
        db.add(material)
        db.flush()
        chapters = [
            Chapter(material_id=material.id, name=name, position=i)
            for i, name in enumerate(("Roots", "Leaves", "Stems"))
        ]
        db.add_all(chapters)
        db.flush()
        db.add_all(
            SessionChapter(session_id=session_id, chapter_id=c.id) for c in chapters
        )
        db.commit()
    assert _plan(client, session_id)["steps"][1]["topic"] == "Roots and 2 more"


def test_weekly_test_on_first_session_of_iso_week(client: TestClient) -> None:
    subject_id = _subject(client)
    _session(client, subject_id, state="ended", started_at=MON)
    tuesday = _session(client, subject_id, started_at=MON + dt.timedelta(days=1))
    next_monday = _session(client, subject_id, started_at=MON + dt.timedelta(days=7))
    assert _plan(client, tuesday)["test_kind"] == "daily"
    assert _plan(client, next_monday)["test_kind"] == "weekly"


def test_week_boundary_uses_family_timezone(client: TestClient) -> None:
    client.app.state.settings.timezone = "Asia/Kolkata"
    subject_id = _subject(client)
    # Sun 23:30 local and Mon 00:10 local are different ISO weeks.
    sunday = dt.datetime(2026, 1, 11, 18, 0)
    _session(client, subject_id, state="ended", started_at=sunday)
    monday = _session(client, subject_id, started_at=sunday + dt.timedelta(minutes=40))
    assert _plan(client, monday)["test_kind"] == "weekly"


def test_surprise_test_before_exam(client: TestClient) -> None:
    client.app.state.clock = FakeClock(MON)
    subject_id = _subject(client)
    with client.app.state.session_factory() as db:
        db.add(Exam(subject_id=subject_id, date=dt.date(2026, 1, 8)))
        db.commit()
    session_id = _session(client, subject_id, state="set_up", started_at=None)
    plan = _plan(client, session_id)
    assert plan["test_kind"] == "surprise"
    assert plan["exam_date"] == "2026-01-08"
    assert plan["steps"][-1]["double_points"] is True


def test_setup_plan_is_rebuilt_after_start(client: TestClient) -> None:
    sunday = dt.datetime(2026, 1, 4, 10, 0)
    client.app.state.clock = FakeClock(sunday)
    subject_id = _subject(client)
    _session(
        client, subject_id, state="ended", started_at=sunday - dt.timedelta(hours=2)
    )
    session_id = _session(client, subject_id, state="set_up", started_at=None)
    assert _plan(client, session_id)["test_kind"] == "daily"
    with client.app.state.session_factory() as db:
        row = db.get(StudySession, session_id)
        row.state = "running"
        row.started_at = MON
        db.commit()
    assert _plan(client, session_id)["test_kind"] == "weekly"


def test_patch_step_and_skip_test_rejected(client: TestClient) -> None:
    session_id = _session(client, _subject(client))
    done = client.patch(
        f"{API}/sessions/{session_id}/plan/steps/warmup", json={"status": "done"}
    )
    assert done.status_code == 200
    assert done.json()["current_step"] == "lesson"
    skip = client.patch(
        f"{API}/sessions/{session_id}/plan/steps/test", json={"status": "skipped"}
    )
    assert skip.status_code == 422
    again = client.patch(
        f"{API}/sessions/{session_id}/plan/steps/warmup", json={"status": "done"}
    )
    assert again.status_code == 409
    unknown = client.patch(
        f"{API}/sessions/{session_id}/plan/steps/nope", json={"status": "done"}
    )
    assert unknown.status_code == 404


def test_patch_requires_running_session(client: TestClient) -> None:
    session_id = _session(client, _subject(client), state="ended")
    r = client.patch(
        f"{API}/sessions/{session_id}/plan/steps/warmup", json={"status": "done"}
    )
    assert r.status_code == 409


def test_progress_with_fake_clock(client: TestClient) -> None:
    clock = FakeClock(MON + dt.timedelta(days=2))
    client.app.state.clock = clock
    subject_id = _subject(client)
    ids = [
        _session(
            client, subject_id, state="ended", started_at=MON + dt.timedelta(days=d)
        )
        for d in range(3)
    ]
    _session(
        client, subject_id, state="force_ended", started_at=MON + dt.timedelta(days=3)
    )
    with client.app.state.session_factory() as db:
        db.add_all(
            [
                Points(session_id=ids[0], reason="test", amount=700),
                Points(session_id=ids[1], reason="warmup", amount=40),
            ]
        )
        db.add(
            StudyTest(
                session_id=ids[0],
                subject_id=subject_id,
                kind="daily",
                status="done",
                graded=True,
                score_pct=100,
            )
        )
        db.commit()
    body = client.get(f"{API}/progress").json()
    assert body["points"] == 740
    assert body["level"]["title"] == "Explorer" and body["level"]["to_next"] == 60
    assert (body["streak_days"], body["completed_sessions"]) == (3, 3)
    assert {"first_session", "streak_3", "perfect_test"} <= set(body["badges"])
    assert body["badge_count"] == len(body["badges"])
    clock.advance(seconds=2 * 86400)
    assert client.get(f"{API}/progress").json()["streak_days"] == 0


def test_progress_starts_empty(client: TestClient) -> None:
    body = client.get(f"{API}/progress").json()
    assert body["points"] == 0 and body["level"]["title"] == "Newcomer"
    assert body["badges"] == []


def test_plan_unknown_session(client: TestClient) -> None:
    assert client.get(f"{API}/sessions/999/plan").status_code == 404
