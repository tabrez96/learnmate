"""Ending a session: the PIN check, lockouts, resending the PIN, force-end and the summary."""

import datetime as dt
import json
from dataclasses import dataclass

from cryptography.fernet import Fernet
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from learnmate.api.family import FAMILY_ID
from learnmate.assess import rules as assess_rules
from learnmate.assess.rules import AssessError
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.models import (
    Family,
    Points,
    SessionEvent,
    StudySession,
    StudyTest,
    Subject,
)
from learnmate.passwords import verify_password
from learnmate.plan import service as plan_service
from learnmate.sessions import rules, service
from learnmate.sessions.pins import read_pin, verify_pin
from learnmate.telegram import templates
from learnmate.telegram.outbox import enqueue

MAX_PASSWORD_LENGTH = 200
ENDABLE_STATES = ("running", "locked")
TIMELINE_TYPES = (
    "started",
    "left",
    "back",
    "locked",
    "unlocked",
    "pin_locked",
    "ended",
)


class EndError(Exception):
    def __init__(
        self, status: int, detail: str | dict, *, retry_after: int | None = None
    ) -> None:
        super().__init__(str(detail))
        self.status = status
        self.detail = detail
        self.retry_after = retry_after


@dataclass(frozen=True)
class Summary:
    studied_min: int
    score_pct: int | None
    band: str | None
    missed: bool
    points: int
    left_count: int
    lock_minutes: tuple[int, ...]
    force_ended: bool
    timeline: tuple[tuple[str, dt.datetime], ...]


def _session(db: Session, session_id: int) -> StudySession:
    row = db.get(StudySession, session_id)
    if row is None:
        raise EndError(404, "Session not found")
    return row


def _endable(row: StudySession) -> None:
    if row.state not in ENDABLE_STATES:
        raise EndError(409, "Session is not running")


def _family(db: Session) -> Family:
    family = db.get(Family, FAMILY_ID)
    if family is None:
        raise EndError(409, "Family not set up")
    return family


def _event(
    db: Session,
    row: StudySession,
    type_: str,
    at: dt.datetime,
    data: dict | None = None,
) -> None:
    db.add(
        SessionEvent(
            session_id=row.id,
            type=type_,
            at=at,
            data_json=json.dumps(data) if data else None,
        )
    )


def pin_status(settings: Settings, row: StudySession, now: dt.datetime) -> dict:
    locked = rules.is_locked(row.pin_locked_until, now)
    return {
        "wrong_pins": row.wrong_pins,
        "tries_left": rules.pin_tries_left(row.wrong_pins, settings.pin_max_wrong),
        "fallback_available": rules.fallback_available(
            row.wrong_pins, settings.pin_wrong_before_fallback
        ),
        "locked_until": row.pin_locked_until.isoformat() if locked else None,
    }


def fallback_status(settings: Settings, family: Family, now: dt.datetime) -> dict:
    locked = rules.is_locked(family.fallback_locked_until, now)
    return {
        "tries_left": settings.fallback_max_wrong - family.fallback_wrong,
        "locked_until": family.fallback_locked_until.isoformat() if locked else None,
    }


def check_pin(
    db: Session,
    settings: Settings,
    clock: Clock,
    row: StudySession,
    pin: str,
) -> None:
    """Return when the PIN is right; otherwise count the try and raise."""
    now = clock.now()
    if rules.is_locked(row.pin_locked_until, now):
        raise EndError(
            423,
            {"message": "The PIN pad is locked", **pin_status(settings, row, now)},
            retry_after=rules.seconds_until(row.pin_locked_until, now),
        )
    if verify_pin(row, pin):
        return
    family = _family(db)
    # Increment in SQL so concurrent wrong PINs cannot overwrite each other's count.
    count = db.execute(
        update(StudySession)
        .where(StudySession.id == row.id)
        .values(wrong_pins=StudySession.wrong_pins + 1)
        .returning(StudySession.wrong_pins)
        .execution_options(synchronize_session=False)
    ).scalar_one()
    set_committed_value(row, "wrong_pins", count)
    _event(db, row, "wrong_pin", now, {"count": count})
    retry_after = None
    if rules.pin_locks_now(count, settings.pin_max_wrong):
        row.pin_locked_until = now + dt.timedelta(seconds=settings.pin_lockout_seconds)
        _event(db, row, "pin_locked", now, {"until": row.pin_locked_until.isoformat()})
        enqueue(
            db,
            templates.pin_lockout(
                family.child_name,
                count,
                templates.clock_time(row.pin_locked_until, settings.timezone),
            ),
        )
        retry_after = rules.seconds_until(row.pin_locked_until, now)
    db.commit()
    status = 423 if retry_after else 403
    message = "The PIN pad is locked" if retry_after else "Wrong PIN"
    raise EndError(
        status,
        {"message": message, **pin_status(settings, row, now)},
        retry_after=retry_after,
    )


def end_session(
    db: Session,
    settings: Settings,
    clock: Clock,
    session_id: int,
    pin: str,
    at: dt.datetime | None = None,
) -> tuple[StudySession, Summary]:
    row = _session(db, session_id)
    _endable(row)
    family = _family(db)
    check_pin(db, settings, clock, row, pin)
    now = clock.now()
    ended_at = rules.offline_end_time(at, row.started_at or now, now)
    spec = _missed_test_spec(db, settings, clock, row)
    summary = _finish(db, settings, family, row, spec, ended_at=ended_at, reason="pin")
    db.commit()
    return row, summary


def resend_pin(
    db: Session,
    settings: Settings,
    clock: Clock,
    cipher: Fernet,
    session_id: int,
) -> dt.datetime:
    """Send the same PIN to Telegram again; returns when the next resend is allowed."""
    row = _session(db, session_id)
    if row.state not in service.ACTIVE_STATES:
        raise EndError(409, "Session is not active")
    family = _family(db)
    now = clock.now()
    interval = dt.timedelta(seconds=settings.pin_resend_interval_seconds)
    if row.pin_last_sent_at is not None:
        next_at = row.pin_last_sent_at + interval
        if now < next_at:
            raise EndError(
                429,
                "The PIN was just sent. Try again in a minute.",
                retry_after=rules.seconds_until(next_at, now),
            )
    pin = read_pin(row, cipher)
    if pin is None:
        raise EndError(409, "The PIN can't be resent. Make a new PIN.")
    enqueue(db, templates.session_pin(family.child_name, pin, row.id, "resent"))
    row.pin_last_sent_at = now
    _event(db, row, "pin_resent", now)
    db.commit()
    return now + interval


def force_end(
    db: Session,
    settings: Settings,
    clock: Clock,
    session_id: int,
    password: str,
    at: dt.datetime | None,
) -> tuple[StudySession, Summary]:
    if len(password) > MAX_PASSWORD_LENGTH:
        # Checked here, not in the request model, so the password is never echoed back.
        raise EndError(422, "The password is too long")
    row = _session(db, session_id)
    _endable(row)
    family = _family(db)
    if family.fallback_hash is None:
        raise EndError(409, "No fallback password is set")
    now = clock.now()
    if rules.is_locked(family.fallback_locked_until, now):
        raise EndError(
            423,
            {
                "message": "The fallback password is locked",
                **fallback_status(settings, family, now),
            },
            retry_after=rules.seconds_until(family.fallback_locked_until, now),
        )
    ended_at = rules.offline_end_time(at, row.started_at or now, now)
    if not verify_password(password, family.fallback_hash):
        # Increment in SQL so concurrent wrong passwords cannot overwrite each other.
        count = db.execute(
            update(Family)
            .where(Family.id == family.id)
            .values(fallback_wrong=Family.fallback_wrong + 1)
            .returning(Family.fallback_wrong)
            .execution_options(synchronize_session=False)
        ).scalar_one()
        set_committed_value(family, "fallback_wrong", count)
        data: dict = {"count": count}
        retry_after = None
        if count >= settings.fallback_max_wrong:
            until = now + dt.timedelta(seconds=settings.fallback_lockout_seconds)
            family.fallback_locked_until = until
            family.fallback_wrong = 0
            data["locked_until"] = until.isoformat()
            enqueue(
                db,
                templates.fallback_lockout(
                    family.child_name,
                    settings.fallback_max_wrong,
                    templates.clock_time(until, settings.timezone),
                ),
            )
            retry_after = rules.seconds_until(until, now)
        _event(db, row, "fallback_wrong", now, data)
        db.commit()
        raise EndError(
            423 if retry_after else 403,
            {
                "message": "The fallback password is locked"
                if retry_after
                else "Wrong password",
                **fallback_status(settings, family, now),
            },
            retry_after=retry_after,
        )
    # The plan is read first (it may commit), before anything below is written.
    spec = _missed_test_spec(db, settings, clock, row)
    family.fallback_wrong = 0
    family.fallback_locked_until = None
    enqueue(
        db,
        templates.force_ended(
            family.child_name, templates.clock_time(ended_at, settings.timezone)
        ),
    )
    summary = _finish(
        db, settings, family, row, spec, ended_at=ended_at, reason="fallback"
    )
    db.commit()
    return row, summary


def _finish(
    db: Session,
    settings: Settings,
    family: Family,
    row: StudySession,
    spec: assess_rules.TestSpec | None,
    *,
    ended_at: dt.datetime,
    reason: str,
) -> Summary:
    """End the session and queue its summary. The caller commits.

    spec is the test to record as missed (see _missed_test_spec, called before any
    write). The conditional update claims the session so only one request ends it.
    """
    new_state = "ended" if reason == "pin" else "force_ended"
    claimed = db.execute(
        update(StudySession)
        .where(StudySession.id == row.id, StudySession.state.in_(ENDABLE_STATES))
        .values(state=new_state)
        .execution_options(synchronize_session=False)
    ).rowcount
    if claimed != 1:
        raise EndError(409, "Session is not running")
    _record_missed_test(db, row, spec, ended_at)
    events = _events(db, row)
    spans = rules.lock_spans(events, ended_at)
    row.state = new_state
    row.end_reason = reason
    row.ended_at = ended_at
    row.study_seconds = rules.study_seconds(row.started_at or ended_at, ended_at, spans)
    row.pin_hash = None
    row.pin_enc = None
    _event(db, row, "ended", ended_at, {"reason": reason})
    db.flush()

    test = db.scalars(
        select(StudyTest)
        .where(StudyTest.session_id == row.id, StudyTest.graded.is_(True))
        .order_by(StudyTest.id.desc())
        .limit(1)
    ).first()
    missed = test is not None and test.status == "missed"
    done = test is not None and test.status == "done"
    score_pct = test.score_pct if done else None
    band = test.band if done else None
    points = db.scalar(
        select(func.coalesce(func.sum(Points.amount), 0)).where(
            Points.session_id == row.id
        )
    )
    # An offline end is synced later: anything recorded after it is not part of the summary.
    all_events = [e for e in _events(db, row) if e[1] <= ended_at]
    summary = Summary(
        studied_min=row.study_seconds // 60,
        score_pct=score_pct,
        band=band,
        missed=missed,
        points=points,
        left_count=sum(
            1 for type_, _ in all_events if type_ in ("left", "heartbeat_lost")
        ),
        lock_minutes=rules.lock_minutes(spans),
        force_ended=reason == "fallback",
        timeline=tuple(e for e in all_events if e[0] in TIMELINE_TYPES),
    )
    subject = db.get(Subject, row.subject_id) if row.subject_id else None
    enqueue(
        db,
        templates.summary(
            templates.SessionSummary(
                child=family.child_name,
                subject=subject.name if subject else "study",
                studied_min=summary.studied_min,
                score_pct=summary.score_pct,
                band=summary.band,
                missed=summary.missed,
                points=summary.points,
                left_count=summary.left_count,
                lock_minutes=summary.lock_minutes,
                force_ended=summary.force_ended,
            )
        ),
    )
    return summary


def _missed_test_spec(
    db: Session, settings: Settings, clock: Clock, row: StudySession
) -> assess_rules.TestSpec | None:
    """The test to record as missed when the session has no graded test yet."""
    has_graded = db.scalar(
        select(StudyTest.id)
        .where(StudyTest.session_id == row.id, StudyTest.graded.is_(True))
        .limit(1)
    )
    if has_graded is not None:
        return None
    try:
        return assess_rules.test_spec(
            plan_service.get_plan(db, settings, clock, row.id)
        )
    except AssessError:
        return None


def _record_missed_test(
    db: Session,
    row: StudySession,
    spec: assess_rules.TestSpec | None,
    ended_at: dt.datetime,
) -> None:
    """An unfinished or never-started test is recorded as missed, with no score."""
    if spec is not None:
        db.add(
            StudyTest(
                session_id=row.id,
                subject_id=row.subject_id,
                kind=spec.kind,
                graded=True,
                status="missed",
                finished_at=ended_at,
            )
        )
    for test in db.scalars(
        select(StudyTest).where(
            StudyTest.session_id == row.id, StudyTest.status == "in_progress"
        )
    ):
        test.status = "missed"
        test.finished_at = ended_at
    db.flush()


def _events(db: Session, row: StudySession) -> list[tuple[str, dt.datetime]]:
    rows = db.execute(
        select(SessionEvent.type, SessionEvent.at)
        .where(SessionEvent.session_id == row.id)
        .order_by(SessionEvent.at, SessionEvent.id)
    )
    return [(r.type, r.at) for r in rows]
