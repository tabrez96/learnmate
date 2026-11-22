"""App presence events, heartbeats and inactivity locks, with their Telegram alerts."""

import datetime as dt
from typing import Literal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.models import Heartbeat, SessionEvent, StudySession
from learnmate.presence import rules
from learnmate.sessions import ending
from learnmate.sessions.ending import EndError
from learnmate.sessions.rules import offline_end_time
from learnmate.telegram import templates
from learnmate.telegram.outbox import enqueue
from learnmate.telegram.templates import clock_time

LIVE_STATES = ("running", "locked")
EventType = Literal["left", "back", "warned", "locked", "unlocked"]


def presence_events(db: Session, row: StudySession) -> list[str]:
    return list(
        db.scalars(
            select(SessionEvent.type)
            .where(
                SessionEvent.session_id == row.id,
                SessionEvent.type.in_(rules.PRESENCE_TYPES),
            )
            .order_by(SessionEvent.at, SessionEvent.id)
        )
    )


def _has_event(
    db: Session, row: StudySession, type_: str, when: dt.datetime, *, later: bool
) -> bool:
    """True if the session has a `type_` event at `when`, or (with `later`) at or after it."""
    at = SessionEvent.at >= when if later else SessionEvent.at == when
    return (
        db.scalar(
            select(SessionEvent.id)
            .where(SessionEvent.session_id == row.id, SessionEvent.type == type_, at)
            .limit(1)
        )
        is not None
    )


def _latest_at(
    db: Session, row: StudySession, types: tuple[str, ...]
) -> dt.datetime | None:
    return db.scalar(
        select(func.max(SessionEvent.at)).where(
            SessionEvent.session_id == row.id, SessionEvent.type.in_(types)
        )
    )


def _beat(db: Session, row: StudySession, now: dt.datetime) -> None:
    beat = db.get(Heartbeat, row.id)
    if beat is None:
        db.add(Heartbeat(session_id=row.id, last_at=now))
    else:
        beat.last_at = now


def _live(db: Session, session_id: int) -> StudySession:
    row = ending._session(db, session_id)
    if row.state not in LIVE_STATES:
        raise EndError(409, "Session is not running")
    return row


def _claim(db: Session, row: StudySession, from_: str, to: str) -> None:
    claimed = db.execute(
        update(StudySession)
        .where(StudySession.id == row.id, StudySession.state == from_)
        .values(state=to)
        .execution_options(synchronize_session=False)
    ).rowcount
    if claimed != 1:
        raise EndError(409, "Session is not running")
    row.state = to


def record_event(
    db: Session,
    settings: Settings,
    clock: Clock,
    session_id: int,
    type_: EventType,
    at: dt.datetime | None,
    pin: str | None,
) -> tuple[StudySession, bool]:
    """Returns (row, recorded). recorded is False for a repeat that changes nothing."""
    row = _live(db, session_id)
    family = ending._family(db)
    now = clock.now()
    when = offline_end_time(at, row.started_at or now, now)
    child = family.child_name
    tz = settings.timezone
    current = rules.presence(presence_events(db, row))
    if type_ == "left":
        if current != "here" or _has_event(db, row, "left", when, later=False):
            return row, False
        ending._event(db, row, "left", when)
        enqueue(db, templates.left_app(child, clock_time(when, tz)))
    elif type_ == "back":
        if current == "here":
            return row, False
        # A return is stored after the departure it answers, whatever the tablet's clock said.
        when = max(when, _latest_at(db, row, rules.PRESENCE_TYPES) or when)
        ending._event(db, row, "back", when)
        enqueue(db, templates.back_in_app(child, clock_time(when, tz)))
    elif type_ == "warned":
        ending._event(db, row, "warned", when)
    elif type_ == "locked":
        # A replay of an old lock must not lock the session again after an unlock.
        if row.state == "locked" or _has_event(db, row, "unlocked", when, later=True):
            return row, False
        _claim(db, row, "running", "locked")
        ending._event(db, row, "locked", when)
        minutes = rules.lock_alert_minutes(family.inactivity_lock_s)
        enqueue(db, templates.locked(child, minutes, clock_time(when, tz)))
    else:
        if pin is None:
            raise EndError(422, "PIN required")
        if row.state != "locked":
            raise EndError(409, "Session is not locked")
        ending.check_pin(db, settings, clock, row, pin)
        _claim(db, row, "locked", "running")
        # An unlock is stored no earlier than the lock it closes, so the lock span closes.
        when = max(when, _latest_at(db, row, ("locked",)) or when)
        ending._event(db, row, "unlocked", when)
        enqueue(db, templates.unlocked(child, clock_time(when, tz)))
    # Any accepted event proves the device is alive, so the watchdog stays quiet.
    _beat(db, row, now)
    db.commit()
    return row, True


def heartbeat(
    db: Session, settings: Settings, clock: Clock, session_id: int
) -> StudySession:
    row = _live(db, session_id)
    now = clock.now()
    _beat(db, row, now)
    if rules.presence(presence_events(db, row)) == "lost":
        # The device is back after a silence the watchdog already reported.
        ending._event(db, row, "back", now)
        enqueue(
            db,
            templates.back_in_app(
                ending._family(db).child_name, clock_time(now, settings.timezone)
            ),
        )
    db.commit()
    return row
