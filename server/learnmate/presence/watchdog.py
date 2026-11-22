"""The watchdog: a running session with no heartbeat for a while counts as left."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from learnmate.api.family import FAMILY_ID
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.models import Family, Heartbeat, StudySession
from learnmate.presence import rules
from learnmate.presence.service import LIVE_STATES, presence_events
from learnmate.sessions import ending
from learnmate.telegram import templates
from learnmate.telegram.outbox import enqueue

log = logging.getLogger(__name__)


def check_silent(db: Session, settings: Settings, clock: Clock) -> list[int]:
    """One pass: send the left alert for every live session silent for the timeout. Returns their ids."""
    now = clock.now()
    family = db.get(Family, FAMILY_ID)
    if family is None:
        return []
    rows = db.execute(
        select(StudySession, Heartbeat.last_at)
        .outerjoin(Heartbeat, Heartbeat.session_id == StudySession.id)
        .where(
            StudySession.state.in_(LIVE_STATES), StudySession.started_at.is_not(None)
        )
    ).all()
    fired: list[int] = []
    for row, last_at in rows:
        last = last_at or row.started_at
        if not rules.is_silent(last, now, settings.heartbeat_timeout_seconds):
            continue
        if rules.presence(presence_events(db, row)) != "here":
            continue
        ending._event(
            db, row, "heartbeat_lost", now, {"last_heartbeat": last.isoformat()}
        )
        enqueue(
            db,
            templates.left_app(
                family.child_name, templates.clock_time(now, settings.timezone)
            ),
        )
        fired.append(row.id)
    db.commit()
    return fired


def _pass(
    session_factory: sessionmaker[Session], settings: Settings, clock: Clock
) -> None:
    with session_factory() as db:
        check_silent(db, settings, clock)


async def watchdog_loop(
    session_factory: sessionmaker[Session], settings: Settings, clock: Clock
) -> None:
    while True:
        try:
            await asyncio.to_thread(_pass, session_factory, settings, clock)
        except Exception:
            log.exception("Watchdog pass failed")
        await asyncio.sleep(settings.watchdog_interval_seconds)
