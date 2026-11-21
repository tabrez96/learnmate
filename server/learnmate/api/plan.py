"""Today's plan, step status and the student's progress."""

import datetime as dt
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from learnmate.api.deps import AppSettings, DbSession
from learnmate.plan import service
from learnmate.plan.rules import PlanError, current_step

router = APIRouter(prefix="/api/v1")


class StepOut(BaseModel):
    key: str
    kind: str
    status: str
    question_count: int | None = None
    topic: str | None = None
    double_points: bool | None = None


class PlanOut(BaseModel):
    session_id: int
    test_kind: str
    exam_date: dt.date | None
    current_step: str | None
    steps: list[StepOut]


class StepPatch(BaseModel):
    status: Literal["done", "skipped"]


class LevelOut(BaseModel):
    number: int
    title: str
    next_title: str
    floor: int
    next_at: int
    to_next: int


class ProgressOut(BaseModel):
    points: int
    streak_days: int
    best_streak_days: int
    completed_sessions: int
    level: LevelOut
    badges: list[str]
    badge_count: int
    completed_challenges: int


def _out(session_id: int, plan: dict) -> PlanOut:
    return PlanOut(
        session_id=session_id,
        test_kind=plan["test_kind"],
        exam_date=plan["exam_date"],
        current_step=current_step(plan),
        steps=plan["steps"],
    )


@router.get("/sessions/{session_id}/plan")
def get_plan(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> PlanOut:
    try:
        plan = service.get_plan(db, settings, request.app.state.clock, session_id)
    except PlanError as e:
        raise HTTPException(e.status, e.detail) from e
    return _out(session_id, plan)


@router.patch("/sessions/{session_id}/plan/steps/{key}")
def patch_step(
    session_id: int,
    key: str,
    body: StepPatch,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> PlanOut:
    try:
        plan = service.patch_step(
            db, settings, request.app.state.clock, session_id, key, body.status
        )
    except PlanError as e:
        raise HTTPException(e.status, e.detail) from e
    return _out(session_id, plan)


@router.get("/progress")
def get_progress(request: Request, db: DbSession, settings: AppSettings) -> ProgressOut:
    return ProgressOut(**service.progress(db, settings, request.app.state.clock))
