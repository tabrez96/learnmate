import datetime as dt

from learnmate.sessions import rules

T0 = dt.datetime(2026, 1, 5, 9, 0)


def test_pin_tries_left_and_locks_every_max() -> None:
    assert [rules.pin_tries_left(n, 5) for n in range(6)] == [5, 4, 3, 2, 1, 5]
    assert [n for n in range(12) if rules.pin_locks_now(n, 5)] == [5, 10]


def test_fallback_available_from_three() -> None:
    assert not rules.fallback_available(2, 3)
    assert rules.fallback_available(3, 3)
    assert rules.fallback_available(7, 3)


def test_is_locked_boundary() -> None:
    until = T0 + dt.timedelta(minutes=15)
    assert rules.is_locked(until, until - dt.timedelta(seconds=1))
    assert not rules.is_locked(until, until)
    assert not rules.is_locked(None, T0)
    assert rules.seconds_until(until, T0) == 900
    assert rules.seconds_until(until, until) == 1


def test_lock_spans_pairs_and_open_lock() -> None:
    m = dt.timedelta(minutes=1)
    events = [
        ("unlocked", T0),
        ("locked", T0 + m),
        ("back", T0 + 2 * m),
        ("unlocked", T0 + 4 * m),
        ("locked", T0 + 10 * m),
    ]
    assert rules.lock_spans(events, T0 + 12 * m) == [180, 120]


def test_lock_spans_stop_at_the_end() -> None:
    m = dt.timedelta(minutes=1)
    end = T0 + 20 * m
    crossing = [("locked", T0 + 10 * m), ("unlocked", T0 + 30 * m)]
    assert rules.lock_spans(crossing, end) == [600]
    after = [
        ("locked", T0 + 20 * m),
        ("unlocked", T0 + 30 * m),
        ("locked", T0 + 25 * m),
    ]
    assert rules.lock_spans(after, end) == []
    closed = [("locked", T0 + 2 * m), ("unlocked", T0 + 5 * m)]
    assert rules.lock_spans(closed, end) == [180]


def test_lock_minutes_rounds_up() -> None:
    assert rules.lock_minutes([20, 300]) == (1, 5)


def test_study_seconds_subtracts_locks() -> None:
    end = T0 + dt.timedelta(minutes=30)
    assert rules.study_seconds(T0, end, [300]) == 1500
    assert rules.study_seconds(T0, end, [5000]) == 0


def test_offline_end_time() -> None:
    now = T0 + dt.timedelta(hours=1)
    assert rules.offline_end_time(None, T0, now) == now
    assert rules.offline_end_time(now + dt.timedelta(minutes=5), T0, now) == now
    aware = dt.datetime(2026, 1, 5, 11, 30, tzinfo=dt.timezone(dt.timedelta(hours=2)))
    assert rules.offline_end_time(aware, T0, now) == dt.datetime(2026, 1, 5, 9, 30)
    assert rules.offline_end_time(T0 - dt.timedelta(minutes=5), T0, now) == T0
    inside = T0 + dt.timedelta(minutes=20)
    assert rules.offline_end_time(inside, T0, now) == inside
