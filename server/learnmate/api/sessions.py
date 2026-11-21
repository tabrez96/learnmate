"""Sessions: create with a PIN, replace the PIN, start, the current session, and ending (PIN, resend, force-end)."""

import datetime as dt
from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from learnmate.api.deps import AppSettings, DbSession
from learnmate.config import Settings
from learnmate.models import StudySession
from learnmate.sessions import ending, rules, service
from learnmate.sessions.service import NewSession, SessionError

router = APIRouter(prefix="/api/v1")


class SessionIn(BaseModel):
    subject_id: int
    type: Literal["learn", "recap", "test_only"]
    material_ids: list[int] = Field(default_factory=list, max_length=50)
    chapter_ids: list[int] = Field(default_factory=list, max_length=200)
    question_count: Literal[5, 10, 15] = 10


class SessionOut(BaseModel):
    id: int
    subject_id: int | None
    type: str
    question_count: int
    state: str
    pin_version: int
    created_at: dt.datetime
    started_at: dt.datetime | None
    material_ids: list[int]
    chapter_ids: list[int]
    wrong_pins: int
    fallback_available: bool
    pin_locked_until: dt.datetime | None
    ended_at: dt.datetime | None
    end_reason: str | None


class SessionWithPinOut(SessionOut):
    pin: str


def _out(
    db: Session, settings: Settings, row: StudySession, now: dt.datetime
) -> SessionOut:
    materials, chapters = service.scope_ids(db, row)
    return SessionOut(
        id=row.id,
        subject_id=row.subject_id,
        type=row.type,
        question_count=row.question_count,
        state=row.state,
        pin_version=row.pin_version,
        created_at=row.created_at,
        started_at=row.started_at,
        material_ids=materials,
        chapter_ids=chapters,
        wrong_pins=row.wrong_pins,
        fallback_available=rules.fallback_available(
            row.wrong_pins, settings.pin_wrong_before_fallback
        ),
        pin_locked_until=(
            row.pin_locked_until if rules.is_locked(row.pin_locked_until, now) else None
        ),
        ended_at=row.ended_at,
        end_reason=row.end_reason,
    )


def _with_pin(
    db: Session, settings: Settings, row: StudySession, now: dt.datetime, pin: str
) -> SessionWithPinOut:
    return SessionWithPinOut(**_out(db, settings, row, now).model_dump(), pin=pin)


@router.post("/sessions", status_code=201)
def create_session(
    body: SessionIn, request: Request, db: DbSession, settings: AppSettings
) -> SessionWithPinOut:
    req = NewSession(
        subject_id=body.subject_id,
        type=body.type,
        material_ids=tuple(body.material_ids),
        chapter_ids=tuple(body.chapter_ids),
        question_count=body.question_count,
    )
    try:
        row, pin = service.create_session(
            db, settings, request.app.state.clock, request.app.state.pin_cipher, req
        )
    except SessionError as e:
        raise HTTPException(e.status, e.detail) from e
    return _with_pin(db, settings, row, request.app.state.clock.now(), pin)


@router.get("/sessions/current")
def get_current_session(
    request: Request, db: DbSession, settings: AppSettings
) -> SessionOut:
    row = service.current_session(db)
    if row is None:
        raise HTTPException(404, "No current session")
    return _out(db, settings, row, request.app.state.clock.now())


@router.post("/sessions/{session_id}/pin")
def replace_session_pin(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> SessionWithPinOut:
    try:
        row, pin = service.replace_pin(
            db,
            settings,
            request.app.state.clock,
            request.app.state.pin_cipher,
            session_id,
            via="app",
        )
    except SessionError as e:
        raise HTTPException(e.status, e.detail) from e
    return _with_pin(db, settings, row, request.app.state.clock.now(), pin)


@router.post("/sessions/{session_id}/start")
def start_session(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> SessionOut:
    try:
        row = service.start_session(db, settings, request.app.state.clock, session_id)
    except SessionError as e:
        raise HTTPException(e.status, e.detail) from e
    return _out(db, settings, row, request.app.state.clock.now())


class EndIn(BaseModel):
    pin: str = Field(pattern=r"^\d{4,12}$")


class ForceEndIn(BaseModel):
    password: str = Field(min_length=1)  # length cap is in ending.force_end
    at: dt.datetime | None = None  # when the force-end happened offline


class TimelineItem(BaseModel):
    type: str
    at: dt.datetime


class SummaryOut(BaseModel):
    studied_min: int
    score_pct: int | None
    band: str | None
    missed: bool
    points: int
    left_count: int
    lock_minutes: list[int]
    force_ended: bool
    timeline: list[TimelineItem]


class EndOut(BaseModel):
    session: SessionOut
    summary: SummaryOut


class ResendOut(BaseModel):
    next_resend_at: dt.datetime


def _raise(e: ending.EndError) -> NoReturn:
    headers = {"Retry-After": str(e.retry_after)} if e.retry_after else None
    raise HTTPException(e.status, e.detail, headers=headers) from e


def _end_out(
    db: Session,
    settings: Settings,
    request: Request,
    row: StudySession,
    summary: ending.Summary,
) -> EndOut:
    return EndOut(
        session=_out(db, settings, row, request.app.state.clock.now()),
        summary=SummaryOut(
            studied_min=summary.studied_min,
            score_pct=summary.score_pct,
            band=summary.band,
            missed=summary.missed,
            points=summary.points,
            left_count=summary.left_count,
            lock_minutes=list(summary.lock_minutes),
            force_ended=summary.force_ended,
            timeline=[TimelineItem(type=t, at=at) for t, at in summary.timeline],
        ),
    )


@router.post("/sessions/{session_id}/end")
def end_session(
    session_id: int,
    body: EndIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> EndOut:
    try:
        row, summary = ending.end_session(
            db, settings, request.app.state.clock, session_id, body.pin
        )
    except ending.EndError as e:
        _raise(e)
    return _end_out(db, settings, request, row, summary)


@router.post("/sessions/{session_id}/pin/resend")
def resend_session_pin(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> ResendOut:
    try:
        next_at = ending.resend_pin(
            db,
            settings,
            request.app.state.clock,
            request.app.state.pin_cipher,
            session_id,
        )
    except ending.EndError as e:
        _raise(e)
    return ResendOut(next_resend_at=next_at)


@router.post("/sessions/{session_id}/force-end")
def force_end_session(
    session_id: int,
    body: ForceEndIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> EndOut:
    try:
        row, summary = ending.force_end(
            db, settings, request.app.state.clock, session_id, body.password, body.at
        )
    except ending.EndError as e:
        _raise(e)
    return _end_out(db, settings, request, row, summary)
