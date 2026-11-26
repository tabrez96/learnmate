import datetime as dt

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.clock import FakeClock
from learnmate.models import (
    Family,
    Outbox,
    SessionEvent,
    StudySession,
    StudyTest,
)
from tests.test_sessions_api import API, _create, _events, _outbox, _row, _setup

T0 = dt.datetime(2026, 1, 5, 9, 0)
PASSWORD = "correct-horse-7731"


def _started(client: TestClient, app: FastAPI) -> tuple[dict, FakeClock]:
    clock = FakeClock(T0)
    app.state.clock = clock
    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    client.post(f"{API}/sessions/{created['id']}/start")
    return created, clock


def _end(client: TestClient, sid: int, pin: str):
    return client.post(f"{API}/sessions/{sid}/end", json={"pin": pin})


def _wrong(pin: str) -> str:
    return "0000" if pin != "0000" else "1111"


def _texts(app: FastAPI) -> list[str]:
    return [m.text for m in _outbox(app)]


def _set_fallback(client: TestClient) -> None:
    client.put(f"{API}/family/fallback", json={"password": PASSWORD})


def _add_test(app: FastAPI, sid: int, **fields) -> None:
    with app.state.session_factory() as db:
        db.add(StudyTest(session_id=sid, kind="daily", graded=True, **fields))
        db.commit()


def _tests(app: FastAPI, sid: int) -> list[StudyTest]:
    with app.state.session_factory() as db:
        return list(db.scalars(select(StudyTest).where(StudyTest.session_id == sid)))


def _add_events(app: FastAPI, sid: int, events: list[tuple[str, int]]) -> None:
    with app.state.session_factory() as db:
        for type_, minutes in events:
            db.add(
                SessionEvent(
                    session_id=sid, type=type_, at=T0 + dt.timedelta(minutes=minutes)
                )
            )
        db.commit()


def test_end_with_pin_ends_and_sends_summary(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    clock.advance(seconds=25 * 60)
    response = _end(client, created["id"], created["pin"])
    assert response.status_code == 200
    body = response.json()
    assert body["session"]["state"] == "ended"
    assert body["session"]["end_reason"] == "pin"
    assert body["session"]["ended_at"] is not None
    assert body["summary"]["studied_min"] == 25
    assert "ended" in [i["type"] for i in body["summary"]["timeline"]]
    row = _row(app, created["id"])
    assert row.pin_hash is None and row.pin_enc is None
    assert _texts(app)[-1].startswith("Session summary:")
    assert "Studied 25 min" in _texts(app)[-1]


def test_end_with_pin_uses_offline_at(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    clock.advance(seconds=30 * 60)
    at = T0 + dt.timedelta(minutes=10)
    response = client.post(
        f"{API}/sessions/{created['id']}/end",
        json={"pin": created["pin"], "at": at.isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["summary"]["studied_min"] == 10
    assert _row(app, created["id"]).ended_at == at


def test_end_with_pin_at_in_future_is_clamped_to_now(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    clock.advance(seconds=30 * 60)
    future = T0 + dt.timedelta(hours=5)
    response = client.post(
        f"{API}/sessions/{created['id']}/end",
        json={"pin": created["pin"], "at": future.isoformat()},
    )
    assert response.status_code == 200
    assert _row(app, created["id"]).ended_at == T0 + dt.timedelta(minutes=30)


def test_wrong_pins_count_and_fallback_after_three(
    client: TestClient, app: FastAPI
) -> None:
    created, _ = _started(client, app)
    bad = _wrong(created["pin"])
    details = []
    for _ in range(3):
        response = _end(client, created["id"], bad)
        assert response.status_code == 403
        details.append(response.json()["detail"])
    assert [d["tries_left"] for d in details] == [4, 3, 2]
    assert [d["fallback_available"] for d in details] == [False, False, True]
    assert len(_events(app, created["id"], "wrong_pin")) == 3
    assert _row(app, created["id"]).wrong_pins == 3


def test_fifth_wrong_pin_locks_for_15_minutes_and_tells_telegram(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    bad = _wrong(created["pin"])
    for _ in range(4):
        assert _end(client, created["id"], bad).status_code == 403
    response = _end(client, created["id"], bad)
    assert response.status_code == 423
    assert (
        response.json()["detail"]["locked_until"]
        == (T0 + dt.timedelta(minutes=15)).isoformat()
    )
    assert response.headers["Retry-After"] == "900"
    locks = [t for t in _texts(app) if "PIN pad is locked until" in t]
    assert len(locks) == 1
    clock.advance(seconds=14 * 60 + 59)
    assert _end(client, created["id"], created["pin"]).status_code == 423
    assert _row(app, created["id"]).wrong_pins == 5
    assert len([t for t in _texts(app) if "PIN pad is locked until" in t]) == 1
    clock.advance(seconds=1)
    assert _end(client, created["id"], created["pin"]).status_code == 200


def test_lockout_repeats_after_expiry(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    bad = _wrong(created["pin"])
    for _ in range(5):
        _end(client, created["id"], bad)
    clock.advance(seconds=15 * 60)
    statuses = [_end(client, created["id"], bad).status_code for _ in range(5)]
    assert statuses == [403, 403, 403, 403, 423]
    assert len([t for t in _texts(app) if "PIN pad is locked until" in t]) == 2
    current = client.get(f"{API}/sessions/current").json()
    assert current["fallback_available"] is True
    assert current["pin_locked_until"] is not None


def test_unfinished_test_recorded_missed_not_zero(
    client: TestClient, app: FastAPI
) -> None:
    created, _ = _started(client, app)
    _add_test(app, created["id"], status="in_progress")
    assert _end(client, created["id"], created["pin"]).status_code == 200
    (test,) = _tests(app, created["id"])
    assert test.status == "missed"
    assert test.score_pct is None and test.band is None
    assert "Test: Missed" in _texts(app)[-1]


def test_no_test_started_creates_missed_test(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    response = _end(client, created["id"], created["pin"])
    assert response.json()["summary"]["missed"] is True
    (test,) = _tests(app, created["id"])
    assert test.graded is True and test.status == "missed"
    assert test.score_pct is None and test.band is None
    assert test.kind in ("daily", "weekly", "surprise")


def test_done_test_keeps_grade_in_summary(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    _add_test(app, created["id"], status="done", score_pct=80, band="B")
    body = _end(client, created["id"], created["pin"]).json()
    assert body["summary"]["score_pct"] == 80 and body["summary"]["band"] == "B"
    assert body["summary"]["missed"] is False
    assert "Test: 80% (B)" in _texts(app)[-1]
    assert len(_tests(app, created["id"])) == 1


def test_summary_counts_left_and_locks(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    _add_events(
        app,
        created["id"],
        [
            ("left", 2),
            ("back", 3),
            ("left", 5),
            ("back", 6),
            ("locked", 10),
            ("unlocked", 15),
        ],
    )
    clock.advance(seconds=30 * 60)
    body = _end(client, created["id"], created["pin"]).json()
    text = _texts(app)[-1]
    assert "Left Learnmate: 2 times" in text
    assert "Locked once for no activity, 5 min" in text
    assert "Studied 25 min" in text
    assert body["summary"]["lock_minutes"] == [5]
    assert body["summary"]["left_count"] == 2
    assert "ended" in [item["type"] for item in body["summary"]["timeline"]]


def test_resend_same_pin_once_a_minute(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    url = f"{API}/sessions/{created['id']}/pin/resend"
    assert client.post(url).status_code == 429
    clock.advance(seconds=61)
    response = client.post(url)
    assert response.status_code == 200
    assert "pin" not in response.json()
    assert f"The session PIN again: {created['pin']}" in _texts(app)[-1]
    again = client.post(url)
    assert again.status_code == 429 and again.headers["Retry-After"] == "60"
    clock.advance(seconds=59)
    assert client.post(url).status_code == 429
    clock.advance(seconds=1)
    assert client.post(url).status_code == 200


def test_resend_requires_active_session(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    _end(client, created["id"], created["pin"])
    assert client.post(f"{API}/sessions/{created['id']}/pin/resend").status_code == 409


def _force(client: TestClient, sid: int, password: str = PASSWORD, **extra):
    return client.post(
        f"{API}/sessions/{sid}/force-end", json={"password": password} | extra
    )


def test_force_end_success_tells_telegram(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    _set_fallback(client)
    response = _force(client, created["id"])
    assert response.status_code == 200
    assert response.json()["session"]["state"] == "force_ended"
    assert response.json()["session"]["end_reason"] == "fallback"
    texts = _texts(app)
    assert any("force-ended with the fallback password" in t for t in texts)
    assert texts[-1].endswith("Force-ended with the fallback password")


def test_three_wrong_passwords_lock_for_an_hour(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    _set_fallback(client)
    sid = created["id"]
    assert _force(client, sid, "nope").status_code == 403
    assert _force(client, sid, "nope").status_code == 403
    third = _force(client, sid, "nope")
    assert third.status_code == 423 and third.headers["Retry-After"] == "3600"
    assert any("fallback password is locked until" in t for t in _texts(app))
    clock.advance(seconds=59 * 60 + 59)
    assert _force(client, sid).status_code == 423
    clock.advance(seconds=1)
    assert _force(client, sid).status_code == 200


def test_offline_force_end_keeps_original_time(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    _set_fallback(client)
    clock.advance(seconds=40 * 60)
    at = T0 + dt.timedelta(minutes=20)
    response = _force(client, created["id"], at=at.isoformat())
    assert response.status_code == 200
    row = _row(app, created["id"])
    assert row.ended_at == at
    assert row.study_seconds == 20 * 60
    with app.state.session_factory() as db:
        ended = db.scalars(
            select(SessionEvent).where(
                SessionEvent.session_id == created["id"], SessionEvent.type == "ended"
            )
        ).one()
    assert ended.at == at


def test_offline_force_end_before_start_is_clamped_to_start(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    _set_fallback(client)
    clock.advance(seconds=600)
    early = (T0 - dt.timedelta(minutes=5)).isoformat()
    assert _force(client, created["id"], at=early).status_code == 200
    row = _row(app, created["id"])
    assert row.state == "force_ended"
    assert row.ended_at == T0 and row.study_seconds == 0


def test_offline_summary_ignores_activity_after_the_end(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    _set_fallback(client)
    _add_events(
        app,
        created["id"],
        [("left", 5), ("back", 6), ("locked", 10), ("unlocked", 30), ("left", 25)],
    )
    clock.advance(seconds=40 * 60)
    at = (T0 + dt.timedelta(minutes=20)).isoformat()
    body = _force(client, created["id"], at=at).json()
    summary = body["summary"]
    assert summary["studied_min"] == 10
    assert summary["left_count"] == 1
    assert summary["lock_minutes"] == [10]
    assert summary["timeline"][-1]["type"] == "ended"


def test_overlong_password_is_rejected_without_echo(
    client: TestClient, app: FastAPI
) -> None:
    created, _ = _started(client, app)
    _set_fallback(client)
    secret = "s3cret-" * 40
    response = _force(client, created["id"], secret)
    assert response.status_code == 422
    assert secret not in response.text
    with app.state.session_factory() as db:
        assert db.get(Family, 1).fallback_wrong == 0


def test_force_end_never_sends_the_password(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    _set_fallback(client)
    wrong = _force(client, created["id"], "wrong-zebra-4412")
    right = _force(client, created["id"])
    assert wrong.status_code == 403
    assert right.status_code == 200
    bodies = [wrong.text, right.text]
    with app.state.session_factory() as db:
        stored = [m.text for m in db.scalars(select(Outbox))]
        stored += [e.data_json or "" for e in db.scalars(select(SessionEvent))]
    for needle in (PASSWORD, "wrong-zebra-4412"):
        assert not any(needle in s for s in stored + bodies)


def test_end_rejected_when_not_running(client: TestClient, app: FastAPI) -> None:
    app.state.clock = FakeClock(T0)
    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    _set_fallback(client)
    assert _end(client, created["id"], created["pin"]).status_code == 409
    assert _force(client, created["id"]).status_code == 409
    assert _end(client, 999, "1234").status_code == 404
    with app.state.session_factory() as db:
        assert db.get(StudySession, created["id"]).state == "set_up"


def test_force_end_without_fallback_password_is_409(
    client: TestClient, app: FastAPI
) -> None:
    created, _ = _started(client, app)
    assert _force(client, created["id"]).status_code == 409


def test_second_end_is_409_and_queues_one_summary(
    client: TestClient, app: FastAPI
) -> None:
    created, _ = _started(client, app)
    assert _end(client, created["id"], created["pin"]).status_code == 200
    assert _end(client, created["id"], created["pin"]).status_code == 409
    summaries = [t for t in _texts(app) if t.startswith("Session summary:")]
    assert len(summaries) == 1
    assert len(_events(app, created["id"], "ended")) == 1
    assert len(_tests(app, created["id"])) == 1
