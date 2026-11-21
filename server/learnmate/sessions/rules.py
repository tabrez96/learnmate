"""Session ending rules: PIN and fallback lockouts, lock spans, study time. Pure: no database, no clock."""

import datetime as dt
import math


def pin_tries_left(wrong: int, max_wrong: int) -> int:
    """Tries before the pad locks. Each lockout gives a fresh set of max_wrong tries."""
    return max_wrong - (wrong % max_wrong)


def pin_locks_now(wrong: int, max_wrong: int) -> bool:
    return wrong > 0 and wrong % max_wrong == 0


def fallback_available(wrong: int, before_fallback: int) -> bool:
    return wrong >= before_fallback


def is_locked(until: dt.datetime | None, now: dt.datetime) -> bool:
    return until is not None and now < until


def seconds_until(until: dt.datetime, now: dt.datetime) -> int:
    return max(1, math.ceil((until - now).total_seconds()))


def lock_spans(events: list[tuple[str, dt.datetime]], end: dt.datetime) -> list[int]:
    """Seconds of each inactivity lock: a 'locked' event up to the next 'unlocked', or to end if still open."""
    spans: list[int] = []
    opened: dt.datetime | None = None
    for type_, at in sorted(events, key=lambda e: e[1]):
        if type_ == "locked" and opened is None:
            opened = at
        elif type_ == "unlocked" and opened is not None:
            spans.append(max(0, int((at - opened).total_seconds())))
            opened = None
    if opened is not None:
        spans.append(max(0, int((end - opened).total_seconds())))
    return spans


def lock_minutes(spans: list[int]) -> tuple[int, ...]:
    return tuple(math.ceil(s / 60) for s in spans)  # a 20-second lock shows as 1 min


def study_seconds(started: dt.datetime, ended: dt.datetime, spans: list[int]) -> int:
    return max(0, int((ended - started).total_seconds()) - sum(spans))


def to_naive_utc(at: dt.datetime) -> dt.datetime:
    return at.astimezone(dt.UTC).replace(tzinfo=None) if at.tzinfo else at


def offline_end_time(
    at: dt.datetime | None, started: dt.datetime, now: dt.datetime
) -> dt.datetime:
    """The time a force-end happened: the client's time if given (clamped to now), else now.

    Raises ValueError when it is before the session started.
    """
    if at is None:
        return now
    at = to_naive_utc(at)
    if at < started:
        raise ValueError("before the session started")
    return min(at, now)
