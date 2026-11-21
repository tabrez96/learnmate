"""Database glue for the plan and progress rules."""

import datetime as dt
import json
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.models import (
    Chapter,
    Exam,
    Material,
    Points,
    SessionChapter,
    SessionMaterial,
    StudySession,
    StudyTest,
)
from learnmate.plan.progress import (
    best_streak,
    current_streak,
    earned_badges,
    level_for,
)
from learnmate.plan.rules import (
    PlanError,
    PlanInput,
    build_plan,
    exam_in_window,
    set_step_status,
)


def local_date(at_utc: dt.datetime, tz: str) -> dt.date:
    return at_utc.replace(tzinfo=dt.UTC).astimezone(ZoneInfo(tz)).date()


def _topic(db: Session, session_id: int) -> str | None:
    names = list(
        db.scalars(
            select(Chapter.name)
            .join(SessionChapter, SessionChapter.chapter_id == Chapter.id)
            .where(SessionChapter.session_id == session_id)
            .order_by(Chapter.material_id, Chapter.position, Chapter.id)
        )
    )
    if not names:
        names = list(
            db.scalars(
                select(Material.title)
                .join(SessionMaterial, SessionMaterial.material_id == Material.id)
                .where(SessionMaterial.session_id == session_id)
                .order_by(Material.id)
            )
        )
    if not names:
        return None
    if len(names) == 1:
        return names[0]
    return f"{names[0]} and {len(names) - 1} more"


def _first_of_week(
    db: Session, settings: Settings, row: StudySession, ref: dt.datetime
) -> bool:
    week = local_date(ref, settings.timezone).isocalendar()[:2]
    earlier = db.scalars(
        select(StudySession.started_at).where(
            StudySession.id != row.id,
            StudySession.state.not_in(("set_up", "cancelled")),
            StudySession.started_at.is_not(None),
            StudySession.started_at >= ref - dt.timedelta(days=8),
            StudySession.started_at < ref,
        )
    )
    return not any(
        local_date(at, settings.timezone).isocalendar()[:2] == week for at in earlier
    )


def get_plan(db: Session, settings: Settings, clock: Clock, session_id: int) -> dict:
    row = db.get(StudySession, session_id)
    if row is None:
        raise PlanError(404, "Session not found")
    if row.plan_json:
        return json.loads(row.plan_json)
    ref = row.started_at or clock.now()
    today = local_date(ref, settings.timezone)
    exam_dates = (
        list(db.scalars(select(Exam.date).where(Exam.subject_id == row.subject_id)))
        if row.subject_id is not None
        else []
    )
    plan = build_plan(
        PlanInput(
            session_type=row.type,
            question_count=row.question_count,
            topic=_topic(db, row.id),
            first_of_week=_first_of_week(db, settings, row, ref),
            exam_date=exam_in_window(today, exam_dates),
        )
    )
    if row.started_at is not None:
        # Before the start the plan is provisional: the start date may change the test kind.
        result = db.execute(
            update(StudySession)
            .where(
                StudySession.id == row.id,
                or_(StudySession.plan_json.is_(None), StudySession.plan_json == ""),
            )
            .values(plan_json=json.dumps(plan))
        )
        db.commit()
        if result.rowcount == 0:
            db.refresh(row)
            return json.loads(row.plan_json)
    return plan


def patch_step(
    db: Session,
    settings: Settings,
    clock: Clock,
    session_id: int,
    key: str,
    status: str,
) -> dict:
    for _ in range(2):
        get_plan(db, settings, clock, session_id)
        row = db.get(StudySession, session_id)
        if row is None or row.state != "running":
            raise PlanError(409, "Session is not running")
        db.refresh(row)
        old_json = row.plan_json
        new = set_step_status(json.loads(old_json), key, status)
        if save_plan(db, session_id, old_json, new):
            db.commit()
            return new
        db.rollback()
    raise PlanError(409, "The session changed. Try again.")


def save_plan(db: Session, session_id: int, old_json: str, new: dict) -> bool:
    """Compare-and-swap on the stored plan; SQLite has no row locks to lean on."""
    result = db.execute(
        update(StudySession)
        .where(StudySession.id == session_id, StudySession.plan_json == old_json)
        .values(plan_json=json.dumps(new))
    )
    return result.rowcount == 1


def completed_days(db: Session, tz: str) -> list[dt.date]:
    """Days of sessions a parent ended; force-ended and cancelled ones don't count."""
    started = db.scalars(
        select(StudySession.started_at).where(
            StudySession.state == "ended", StudySession.started_at.is_not(None)
        )
    )
    return [local_date(at, tz) for at in started]


def progress(db: Session, settings: Settings, clock: Clock) -> dict:
    points = int(db.scalar(select(func.coalesce(func.sum(Points.amount), 0))) or 0)
    days = completed_days(db, settings.timezone)
    today = local_date(clock.now(), settings.timezone)
    perfect = db.scalar(
        select(func.count())
        .select_from(StudyTest)
        .where(
            StudyTest.graded.is_(True),
            StudyTest.status == "done",
            StudyTest.score_pct == 100,
        )
    )
    level = level_for(points)
    best = best_streak(days)
    badges = earned_badges(
        completed_sessions=len(days),
        best_streak=best,
        perfect_tests=perfect or 0,
        points=points,
    )
    return {
        "points": points,
        "streak_days": current_streak(days, today),
        "best_streak_days": best,
        "completed_sessions": len(days),
        "level": {
            "number": level.number,
            "title": level.title,
            "next_title": level.next_title,
            "floor": level.floor,
            "next_at": level.next_at,
            "to_next": level.to_next,
        },
        "badges": badges,
        "badge_count": len(badges),
    }
