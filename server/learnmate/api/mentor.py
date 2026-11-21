"""The mentor's lesson and its quick checks."""

import datetime as dt
import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from learnmate.api.deps import AppSettings, DbSession
from learnmate.api.family import FAMILY_ID
from learnmate.mentor import chat, service
from learnmate.mentor.lesson import MentorError, lesson_step
from learnmate.models import Family, Message
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


class MessageIn(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
    mode: Literal["books", "outside"] = "books"


class MessageOut(BaseModel):
    id: int
    role: Literal["mentor", "student"]
    text: str
    sources: list[SourceOut]
    visual: dict[str, Any] | None
    outside: bool
    source_url: str | None
    can_check_outside: bool
    created_at: dt.datetime


class PostMessageOut(BaseModel):
    question: MessageOut
    answer: MessageOut


def _message_out(message: Message, family: Family | None) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,  # type: ignore[arg-type]
        text=message.text,
        sources=json.loads(message.sources_json or "[]"),
        visual=json.loads(message.visual_json) if message.visual_json else None,
        outside=message.outside,
        source_url=message.outside_source_url,
        can_check_outside=chat.can_check_outside(message, family),
        created_at=message.created_at,
    )


@router.post("/sessions/{session_id}/mentor/messages")
def post_message(
    session_id: int,
    body: MessageIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> PostMessageOut:
    state = request.app.state
    try:
        student, mentor = chat.post_message(
            db,
            settings,
            state.clock,
            state.llm,
            state.embedder,
            state.reranker,
            session_id,
            body.text,
            body.mode,
        )
    except (MentorError, PlanError) as e:
        raise HTTPException(e.status, e.detail) from e
    family = db.get(Family, FAMILY_ID)
    return PostMessageOut(
        question=_message_out(student, family), answer=_message_out(mentor, family)
    )


@router.get("/sessions/{session_id}/mentor/messages")
def get_messages(session_id: int, db: DbSession) -> list[MessageOut]:
    try:
        messages = chat.list_messages(db, session_id)
    except MentorError as e:
        raise HTTPException(e.status, e.detail) from e
    family = db.get(Family, FAMILY_ID)
    return [_message_out(m, family) for m in messages]
