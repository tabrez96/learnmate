import datetime as dt

from learnmate.presence.rules import is_silent, lock_alert_minutes, presence


def test_presence_defaults_to_here() -> None:
    assert presence([]) == "here"
    assert presence(["started"]) == "here"


def test_presence_follows_last_event() -> None:
    assert presence(["left"]) == "left"
    assert presence(["left", "back"]) == "here"
    assert presence(["heartbeat_lost"]) == "lost"
    assert presence(["heartbeat_lost", "back", "left"]) == "left"


def test_is_silent_at_timeout() -> None:
    now = dt.datetime(2026, 1, 5, 9, 0)
    assert not is_silent(now - dt.timedelta(seconds=44), now, 45)
    assert is_silent(now - dt.timedelta(seconds=45), now, 45)


def test_lock_alert_minutes() -> None:
    assert lock_alert_minutes(300) == 5
    assert lock_alert_minutes(30) == 1
