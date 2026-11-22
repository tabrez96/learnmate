import asyncio
import contextlib
import datetime as dt

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.models import Heartbeat, SessionEvent
from learnmate.presence.watchdog import check_silent, watchdog_loop
from tests.test_session_end_api import T0, _end, _started, _texts, _wrong
from tests.test_sessions_api import API, _events, _outbox, _row


def _post(client: TestClient, sid: int, type_: str, **extra):
    return client.post(f"{API}/sessions/{sid}/events", json={"type": type_, **extra})


def _at(minutes: int) -> str:
    return (T0 + dt.timedelta(minutes=minutes)).isoformat()


def _beat(client: TestClient, sid: int):
    return client.post(f"{API}/sessions/{sid}/heartbeat")


def _check(app: FastAPI, clock) -> list[int]:
    with app.state.session_factory() as db:
        return check_silent(db, app.state.settings, clock)


def test_left_queues_alert(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    response = _post(client, created["id"], "left")
    assert response.status_code == 200
    assert response.json() == {"state": "running", "recorded": True}
    assert _texts(app)[-1] == "Sam left Learnmate during the session (09:00)."


def test_back_queues_alert(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    _post(client, created["id"], "left")
    clock.advance(seconds=120)
    assert _post(client, created["id"], "back").json()["recorded"] is True
    assert _texts(app)[-1] == "Sam is back (09:02)."


def test_back_while_here_is_not_recorded(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    before = len(_outbox(app))
    assert _post(client, created["id"], "back").json()["recorded"] is False
    assert len(_outbox(app)) == before


def test_repeated_left_sends_one_alert(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    assert _post(client, created["id"], "left").json()["recorded"] is True
    assert _post(client, created["id"], "left").json()["recorded"] is False
    assert sum("left Learnmate" in t for t in _texts(app)) == 1


def test_locked_and_unlocked_alerts(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    clock.advance(seconds=10 * 60)
    response = _post(client, created["id"], "locked")
    assert response.json() == {"state": "locked", "recorded": True}
    assert (
        _texts(app)[-1]
        == "Sam's session locked after 5 minutes with no activity (09:10)."
    )
    assert _post(client, created["id"], "locked").json()["recorded"] is False
    clock.advance(seconds=4 * 60)
    response = _post(client, created["id"], "unlocked", pin=created["pin"])
    assert response.json() == {"state": "running", "recorded": True}
    assert _texts(app)[-1] == "Sam's session was unlocked (09:14)."


def test_locked_alert_uses_family_lock_setting(
    client: TestClient, app: FastAPI
) -> None:
    from learnmate.models import Family

    created, clock = _started(client, app)
    with app.state.session_factory() as db:
        db.scalars(select(Family)).one().inactivity_lock_s = 600
        db.commit()
    clock.advance(seconds=10 * 60)
    _post(client, created["id"], "locked")
    assert (
        _texts(app)[-1]
        == "Sam's session locked after 10 minutes with no activity (09:10)."
    )


def test_locked_on_set_up_session_is_refused(client: TestClient, app: FastAPI) -> None:
    from tests.test_sessions_api import _create, _setup

    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    assert _post(client, created["id"], "locked").status_code == 409


def test_warned_records_event_without_message(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    before = len(_outbox(app))
    assert _post(client, created["id"], "warned").json()["recorded"] is True
    assert len(_events(app, created["id"], "warned")) == 1
    assert len(_outbox(app)) == before


def test_unlock_wrong_pin_counts_toward_end_lockout(
    client: TestClient, app: FastAPI
) -> None:
    created, _ = _started(client, app)
    sid, bad = created["id"], _wrong(created["pin"])
    _post(client, sid, "locked")
    for _ in range(3):
        assert _post(client, sid, "unlocked", pin=bad).status_code == 403
    assert _end(client, sid, bad).status_code == 403
    last = _end(client, sid, bad)
    assert last.status_code == 423
    assert last.headers["Retry-After"]
    assert _row(app, sid).wrong_pins == 5
    assert sum("wrong PINs" in t for t in _texts(app)) == 1
    assert _post(client, sid, "unlocked", pin=created["pin"]).status_code == 423


def test_unlock_requires_pin_and_locked_state(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    sid = created["id"]
    _post(client, sid, "locked")
    assert _post(client, sid, "unlocked").status_code == 422
    _post(client, sid, "unlocked", pin=created["pin"])
    assert _post(client, sid, "unlocked", pin=_wrong(created["pin"])).status_code == 409
    assert _row(app, sid).wrong_pins == 0


def test_client_time_is_clamped(client: TestClient, app: FastAPI) -> None:
    created, _ = _started(client, app)
    _post(client, created["id"], "left", at=_at(60))
    with app.state.session_factory() as db:
        event = db.scalar(select(SessionEvent).where(SessionEvent.type == "left"))
        assert event.at == T0


def test_locked_minutes_excluded_from_study_time(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    clock.advance(seconds=16 * 60)
    _post(client, sid, "locked", at=_at(10))
    _post(client, sid, "unlocked", at=_at(16), pin=created["pin"])
    clock.advance(seconds=14 * 60)
    summary = _end(client, sid, created["pin"]).json()["summary"]
    assert summary["studied_min"] == 24
    assert summary["lock_minutes"] == [6]


def test_open_lock_excluded_when_ending_locked(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    clock.advance(seconds=20 * 60)
    _post(client, sid, "locked")
    clock.advance(seconds=10 * 60)
    summary = _end(client, sid, created["pin"]).json()["summary"]
    assert summary["studied_min"] == 20


def test_heartbeat_upserts_and_rejects_ended(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    assert _beat(client, sid).json() == {"state": "running"}
    clock.advance(seconds=30)
    _beat(client, sid)
    with app.state.session_factory() as db:
        beats = list(db.scalars(select(Heartbeat)))
        assert len(beats) == 1
        assert beats[0].last_at == T0 + dt.timedelta(seconds=30)
    _end(client, sid, created["pin"])
    assert _beat(client, sid).status_code == 409
    assert _post(client, sid, "left").status_code == 409


def test_watchdog_fires_once_per_silence(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    _beat(client, sid)
    clock.advance(seconds=44)
    assert _check(app, clock) == []
    clock.advance(seconds=1)
    assert _check(app, clock) == [sid]
    assert len(_events(app, sid, "heartbeat_lost")) == 1
    assert sum("left Learnmate" in t for t in _texts(app)) == 1
    clock.advance(seconds=60)
    assert _check(app, clock) == []
    _beat(client, sid)
    assert _texts(app)[-1] == "Sam is back (09:01)."
    clock.advance(seconds=45)
    assert _check(app, clock) == [sid]
    assert len(_events(app, sid, "heartbeat_lost")) == 2


def test_watchdog_skips_left_and_set_up(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    _post(client, created["id"], "left")
    clock.advance(seconds=300)
    assert _check(app, clock) == []
    assert _events(app, created["id"], "heartbeat_lost") == []


def test_watchdog_skips_set_up_session(client: TestClient, app: FastAPI) -> None:
    from learnmate.clock import FakeClock
    from tests.test_sessions_api import _create, _setup

    clock = FakeClock(T0)
    app.state.clock = clock
    _create(client, _setup(client, app))
    clock.advance(seconds=300)
    assert _check(app, clock) == []


def test_watchdog_counts_in_summary(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    clock.advance(seconds=60)
    _check(app, clock)
    summary = _end(client, created["id"], created["pin"]).json()["summary"]
    assert summary["left_count"] == 1


def test_watchdog_loop_runs_and_stops(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    clock.advance(seconds=60)
    settings = app.state.settings.model_copy(update={"watchdog_interval_seconds": 0.01})

    async def run() -> None:
        task = asyncio.create_task(
            watchdog_loop(app.state.session_factory, settings, clock)
        )
        try:
            deadline = asyncio.get_running_loop().time() + 2
            while (
                not _events(app, created["id"], "heartbeat_lost")
                and asyncio.get_running_loop().time() < deadline
            ):
                await asyncio.sleep(0.01)
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    asyncio.run(run())
    assert len(_events(app, created["id"], "heartbeat_lost")) == 1


def test_replayed_left_after_back_is_ignored(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    _post(client, sid, "left", at=_at(0))
    clock.advance(seconds=120)
    _post(client, sid, "back", at=_at(2))
    assert _post(client, sid, "left", at=_at(0)).json()["recorded"] is False
    assert sum("left Learnmate" in t for t in _texts(app)) == 1
    clock.advance(seconds=60)
    assert _post(client, sid, "left", at=_at(3)).json()["recorded"] is True


def test_replayed_lock_after_unlock_is_ignored(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    clock.advance(seconds=20 * 60)
    _post(client, sid, "locked", at=_at(10))
    _post(client, sid, "unlocked", at=_at(15), pin=created["pin"])
    response = _post(client, sid, "locked", at=_at(10))
    assert response.json() == {"state": "running", "recorded": False}
    assert _post(client, sid, "locked", at=_at(18)).json()["state"] == "locked"


def test_back_event_keeps_watchdog_quiet(client: TestClient, app: FastAPI) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    _beat(client, sid)
    clock.advance(seconds=45)
    assert _check(app, clock) == [sid]
    clock.advance(seconds=1)
    _post(client, sid, "back")
    clock.advance(seconds=10)
    assert _check(app, clock) == []
    assert len(_events(app, sid, "heartbeat_lost")) == 1


def test_back_after_watchdog_loss_is_ordered_after_it(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    _beat(client, sid)
    clock.advance(seconds=45)
    assert _check(app, clock) == [sid]
    clock.advance(seconds=30)
    assert _post(client, sid, "back", at=_at(0)).json()["recorded"] is True
    clock.advance(seconds=1)
    texts = len(_texts(app))
    _beat(client, sid)
    assert len(_texts(app)) == texts
    assert _post(client, sid, "left").json()["recorded"] is True
    assert _texts(app)[-1].startswith("Sam left Learnmate")


def test_unlock_is_stored_no_earlier_than_its_lock(
    client: TestClient, app: FastAPI
) -> None:
    created, clock = _started(client, app)
    sid = created["id"]
    clock.advance(seconds=30 * 60)
    _post(client, sid, "locked", at=_at(10))
    _post(client, sid, "unlocked", at=_at(5), pin=created["pin"])
    summary = _end(client, sid, created["pin"]).json()["summary"]
    assert summary["lock_minutes"] == [0]
    assert summary["studied_min"] == 30
