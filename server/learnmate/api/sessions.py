"""Session set-up: create with a PIN, replace the PIN, start, and the current session."""

import datetime as dt
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from learnmate.api.deps import AppSettings, DbSession
from learnmate.models import StudySession
from learnmate.sessions import service
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


class SessionWithPinOut(SessionOut):
    pin: str


def _out(db: Session, row: StudySession) -> SessionOut:
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
    )


def _with_pin(db: Session, row: StudySession, pin: str) -> SessionWithPinOut:
    return SessionWithPinOut(**_out(db, row).model_dump(), pin=pin)


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
    return _with_pin(db, row, pin)


@router.get("/sessions/current")
def get_current_session(db: DbSession) -> SessionOut:
    row = service.current_session(db)
    if row is None:
        raise HTTPException(404, "No current session")
    return _out(db, row)


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
    return _with_pin(db, row, pin)


@router.post("/sessions/{session_id}/start")
def start_session(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> SessionOut:
    try:
        row = service.start_session(db, settings, request.app.state.clock, session_id)
    except SessionError as e:
        raise HTTPException(e.status, e.detail) from e
    return _out(db, row)
