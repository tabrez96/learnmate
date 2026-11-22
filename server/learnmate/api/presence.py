"""Presence: app events (left, back, warned, locked, unlocked) and heartbeats."""

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from learnmate.api.deps import AppSettings, DbSession
from learnmate.api.sessions import _raise
from learnmate.presence import service
from learnmate.sessions.ending import EndError

router = APIRouter(prefix="/api/v1")


class EventIn(BaseModel):
    type: Literal["left", "back", "warned", "locked", "unlocked"]
    at: dt.datetime | None = (
        None  # when it happened on the tablet (queued events arrive late)
    )
    pin: str | None = Field(None, pattern=r"^\d{4,12}$")  # only for unlocked


class EventOut(BaseModel):
    state: str
    recorded: bool


class HeartbeatOut(BaseModel):
    state: str


@router.post("/sessions/{session_id}/events")
def post_event(
    session_id: int,
    body: EventIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> EventOut:
    try:
        row, recorded = service.record_event(
            db,
            settings,
            request.app.state.clock,
            session_id,
            body.type,
            body.at,
            body.pin,
        )
    except EndError as e:
        _raise(e)
    return EventOut(state=row.state, recorded=recorded)


@router.post("/sessions/{session_id}/heartbeat")
def post_heartbeat(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> HeartbeatOut:
    try:
        row = service.heartbeat(db, settings, request.app.state.clock, session_id)
    except EndError as e:
        _raise(e)
    return HeartbeatOut(state=row.state)
