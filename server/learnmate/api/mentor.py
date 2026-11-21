"""The mentor's lesson and its quick checks."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from learnmate.api.deps import AppSettings, DbSession
from learnmate.mentor import service
from learnmate.mentor.lesson import MentorError, lesson_step
from learnmate.plan.progress import QUICK_CHECK_POINTS
from learnmate.plan.rules import PlanError

router = APIRouter(prefix="/api/v1")


class CheckOut(BaseModel):
    prompt: str
    options: list[str]
    answer_index: int | None
    correct_index: int | None  # null until answered
    explanation: str | None  # null until answered


class SourceOut(BaseModel):
    passage_id: int
    material: str
    chapter: str
    page: int | None


class LessonStepOut(BaseModel):
    index: int
    title: str
    body: str
    check: CheckOut
    sources: list[SourceOut]


class LessonOut(BaseModel):
    session_id: int
    topic: str | None
    steps: list[LessonStepOut]


class AnswerIn(BaseModel):
    answer_index: int = Field(ge=0, le=3)


class AnswerOut(BaseModel):
    correct: bool
    correct_index: int
    explanation: str
    points_awarded: int


def _lesson_out(session_id: int, plan: dict) -> LessonOut:
    step = lesson_step(plan)
    steps = []
    for i, s in enumerate(step["lesson"]["steps"]):
        check = s["check"]
        answered = s["answer_index"] is not None
        steps.append(
            LessonStepOut(
                index=i,
                title=s["title"],
                body=s["body"],
                check=CheckOut(
                    prompt=check["prompt"],
                    options=check["options"],
                    answer_index=s["answer_index"],
                    correct_index=check["correct_index"] if answered else None,
                    explanation=check["explanation"] if answered else None,
                ),
                sources=s["sources"],
            )
        )
    return LessonOut(session_id=session_id, topic=step.get("topic"), steps=steps)


@router.post("/sessions/{session_id}/mentor/lesson")
def start_lesson(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> LessonOut:
    state = request.app.state
    try:
        plan = service.start_lesson(
            db, settings, state.clock, state.llm, state.embedder, session_id
        )
    except (MentorError, PlanError) as e:
        raise HTTPException(e.status, e.detail) from e
    return _lesson_out(session_id, plan)


@router.post("/sessions/{session_id}/mentor/lesson/steps/{index}/answer")
def answer_check(
    session_id: int,
    index: int,
    body: AnswerIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> AnswerOut:
    try:
        plan, correct = service.answer(
            db, settings, request.app.state.clock, session_id, index, body.answer_index
        )
    except (MentorError, PlanError) as e:
        raise HTTPException(e.status, e.detail) from e
    check = lesson_step(plan)["lesson"]["steps"][index]["check"]
    return AnswerOut(
        correct=correct,
        correct_index=check["correct_index"],
        explanation=check["explanation"],
        points_awarded=QUICK_CHECK_POINTS if correct else 0,
    )
