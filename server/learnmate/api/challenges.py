"""Ungraded challenges: the warm-up, the S04 challenge card and the S07 bonus."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from learnmate.api import assess
from learnmate.api.assess import TestOut
from learnmate.api.deps import AppSettings, DbSession
from learnmate.assess.rules import AssessError
from learnmate.challenges import service
from learnmate.plan.rules import PlanError

router = APIRouter(prefix="/api/v1")


class ChallengeIn(BaseModel):
    kind: Literal["warmup", "challenge", "bonus"]


@router.post("/sessions/{session_id}/challenges")
def create_challenge(
    session_id: int,
    body: ChallengeIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> TestOut:
    state = request.app.state
    try:
        test = service.create_challenge(
            db, settings, state.clock, state.llm, state.embedder, session_id, body.kind
        )
    except (AssessError, PlanError) as e:
        raise HTTPException(e.status, e.detail) from e
    return assess.test_out(db, test)
