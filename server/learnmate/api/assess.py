"""Graded tests: make one, answer it question by question, resume it."""

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from learnmate.api.deps import AppSettings, DbSession
from learnmate.assess import service
from learnmate.assess.rules import AssessError
from learnmate.challenges.rules import challenge_points
from learnmate.models import Question, StudyTest
from learnmate.plan.progress import test_points
from learnmate.plan.rules import PlanError

router = APIRouter(prefix="/api/v1")


class SourceOut(BaseModel):
    material: str
    chapter: str
    page: int | None


class TestQuestionOut(BaseModel):
    position: int
    prompt: str
    options: list[str]
    answer_index: int | None
    correct_index: int | None  # null until answered
    explanation: str | None  # null until answered
    source: SourceOut | None  # null until answered, or when the chunk was deleted


class ResultOut(BaseModel):
    score_pct: int
    band: str
    right: int
    total: int
    points: int
    grade_queued: bool


class TestOut(BaseModel):
    id: int
    session_id: int | None
    kind: str
    status: str
    total: int
    current_index: int
    points_so_far: int
    questions: list[TestQuestionOut]
    result: ResultOut | None  # set when status == "done"


class TestAnswerIn(BaseModel):
    position: int = Field(ge=0)
    answer_index: int = Field(ge=0, le=3)


class TestAnswerOut(BaseModel):
    correct: bool
    correct_index: int
    explanation: str
    source: SourceOut | None
    points_so_far: int
    finished: bool
    test: TestOut


def _right(questions: list[Question]) -> int:
    return sum(q.answer_index == q.correct_index for q in questions)


def _points(test: StudyTest, questions: list[Question]) -> int:
    if not test.graded:
        return challenge_points(_right(questions))
    return test_points(_right(questions), double_points=test.kind == "surprise")


def _source(sources: dict[int, dict], question: Question) -> SourceOut | None:
    found = sources.get(question.chunk_id) if question.chunk_id is not None else None
    return SourceOut(**found) if found else None


def test_out(db: DbSession, test: StudyTest) -> TestOut:
    questions = service.questions_of(db, test.id)
    sources = service.sources_of(db, [q.chunk_id for q in questions if q.chunk_id])
    out = []
    for q in questions:
        answered = q.answer_index is not None
        out.append(
            TestQuestionOut(
                position=q.position,
                prompt=q.prompt,
                options=json.loads(q.options_json),
                answer_index=q.answer_index,
                correct_index=q.correct_index if answered else None,
                explanation=q.explanation if answered else None,
                source=_source(sources, q) if answered else None,
            )
        )
    points = _points(test, questions)
    result = None
    if test.status == "done" and test.score_pct is not None and test.band:
        result = ResultOut(
            score_pct=test.score_pct,
            band=test.band,
            right=_right(questions),
            total=len(questions),
            points=points,
            grade_queued=test.session_id is not None,
        )
    return TestOut(
        id=test.id,
        session_id=test.session_id,
        kind=test.kind,
        status=test.status,
        total=len(questions),
        current_index=test.current_index,
        points_so_far=points,
        questions=out,
        result=result,
    )


@router.post("/sessions/{session_id}/tests")
def create_test(
    session_id: int, request: Request, db: DbSession, settings: AppSettings
) -> TestOut:
    state = request.app.state
    try:
        test = service.create_test(
            db, settings, state.clock, state.llm, state.embedder, session_id
        )
    except (AssessError, PlanError) as e:
        raise HTTPException(e.status, e.detail) from e
    return test_out(db, test)


@router.get("/tests/{test_id}")
def get_test(test_id: int, db: DbSession) -> TestOut:
    try:
        test = service.get_test(db, test_id)
    except AssessError as e:
        raise HTTPException(e.status, e.detail) from e
    return test_out(db, test)


@router.post("/tests/{test_id}/answers")
def post_answer(
    test_id: int,
    body: TestAnswerIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> TestAnswerOut:
    try:
        result = service.answer(
            db,
            settings,
            request.app.state.clock,
            test_id,
            body.position,
            body.answer_index,
        )
    except (AssessError, PlanError) as e:
        raise HTTPException(e.status, e.detail) from e
    q = result.question
    test = service.get_test(db, test_id)
    sources = service.sources_of(db, [q.chunk_id] if q.chunk_id else [])
    out = test_out(db, test)
    return TestAnswerOut(
        correct=q.answer_index == q.correct_index,
        correct_index=q.correct_index,
        explanation=q.explanation or "",
        source=_source(sources, q),
        points_so_far=out.points_so_far,
        finished=result.finished,
        test=out,
    )
