"""Database glue for tests: generating, answering and grading."""

import json
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.assess import rules
from learnmate.challenges import rules as challenge_rules
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.types import Llm, LlmError, Passage
from learnmate.llm.types import Question as LlmQuestion
from learnmate.mentor import service as mentor_service
from learnmate.mentor.lesson import ScopeChunk, select_passages
from learnmate.models import (
    Chapter,
    Chunk,
    Family,
    Material,
    Points,
    Question,
    StudySession,
    StudyTest,
)
from learnmate.plan import service as plan_service
from learnmate.plan.progress import test_points
from learnmate.plan.rules import TEST_STEP, set_step_status
from learnmate.rag.embed import Embedder
from learnmate.telegram import templates
from learnmate.telegram.outbox import enqueue


def _existing(db: Session, session_id: int, kind: str) -> StudyTest | None:
    return db.scalars(
        select(StudyTest)
        .where(
            StudyTest.session_id == session_id,
            StudyTest.kind == kind,
            StudyTest.graded.is_(True),
        )
        .order_by(StudyTest.id.desc())
    ).first()


def make_questions(
    llm: Llm,
    scope: list[ScopeChunk],
    passages: list[Passage],
    count: int,
    grade: int,
) -> list[LlmQuestion]:
    allowed = {p.id for p in passages}
    chapter_of = {c.id: c.key for c in scope}
    kept: list = []
    seen: set[str] = set()
    # No budget check: a running session must be able to finish with its test.
    try:
        for _ in range(rules.GENERATE_ATTEMPTS):
            missing = count - len(kept)
            if missing <= 0:
                break
            result = llm.generate_questions(
                passages=passages,
                count=missing if kept else count,
                grade=grade,
            ).value
            kept += rules.valid_questions(result.questions, allowed, seen)
    except LlmError as e:
        raise rules.AssessError(502, "The test couldn't be made. Try again.") from e
    if len(kept) < count:
        raise rules.AssessError(
            502, "The test couldn't be made from your material. Try again."
        )
    return rules.spread(kept, chapter_of, count)


def store_questions(db: Session, test: StudyTest, chosen: list[LlmQuestion]) -> None:
    for i, q in enumerate(chosen):
        db.add(
            Question(
                test_id=test.id,
                position=i,
                prompt=q.prompt,
                options_json=json.dumps(q.options),
                correct_index=q.correct_index,
                explanation=q.explanation,
                chunk_id=q.passage_id,
            )
        )


def create_test(
    db: Session,
    settings: Settings,
    clock: Clock,
    llm: Llm,
    embedder: Embedder,
    session_id: int,
) -> StudyTest:
    row = db.get(StudySession, session_id)
    if row is None:
        raise rules.AssessError(404, "Session not found")
    if row.state != "running":
        raise rules.AssessError(409, "Session is not running")
    plan = plan_service.get_plan(db, settings, clock, session_id)
    spec = rules.test_spec(plan)
    existing = _existing(db, session_id, spec.kind)
    if existing is not None:
        return existing
    step = next(s for s in plan["steps"] if s["key"] == TEST_STEP)
    if step["status"] != "pending":
        raise rules.AssessError(409, "The test is already finished")
    family = db.get(Family, FAMILY_ID)
    if family is None:
        raise rules.AssessError(409, "Family not set up")
    scope = mentor_service.scope_chunks(db, row)
    passages = select_passages(scope, mentor_service.retriever(db, settings, embedder))
    if not passages:
        raise rules.AssessError(422, "There's no material to test from yet")
    chosen = make_questions(llm, scope, passages, spec.count, family.grade)
    existing = _existing(db, session_id, spec.kind)  # a parallel request may have won
    if existing is not None:
        return existing
    test = StudyTest(
        session_id=row.id, subject_id=row.subject_id, kind=spec.kind, graded=True
    )
    db.add(test)
    db.flush()
    store_questions(db, test, chosen)
    db.commit()
    return test


@dataclass(frozen=True)
class AnswerResult:
    question: Question  # the model row, after saving
    finished: bool  # this answer finished the test


def get_test(db: Session, test_id: int) -> StudyTest:
    test = db.get(StudyTest, test_id)
    if test is None:
        raise rules.AssessError(404, "Test not found")
    return test


def questions_of(db: Session, test_id: int) -> list[Question]:
    return list(
        db.scalars(
            select(Question)
            .where(Question.test_id == test_id)
            .order_by(Question.position)
        )
    )


def sources_of(db: Session, chunk_ids: list[int]) -> dict[int, dict]:
    rows = db.execute(
        select(Chunk.id, Material.title, Chapter.name, Chunk.page)
        .join(Material, Chunk.material_id == Material.id)
        .outerjoin(Chapter, Chunk.chapter_id == Chapter.id)
        .where(Chunk.id.in_(chunk_ids))
    )
    return {
        cid: {"material": title, "chapter": name or "", "page": page}
        for cid, title, name, page in rows
    }


def answer(
    db: Session,
    settings: Settings,
    clock: Clock,
    test_id: int,
    position: int,
    answer_index: int,
) -> AnswerResult:
    test = get_test(db, test_id)
    question = db.scalars(
        select(Question).where(
            Question.test_id == test_id, Question.position == position
        )
    ).first()
    if question is None:
        raise rules.AssessError(404, "Question not found")
    if question.answer_index is not None:
        return AnswerResult(question, False)  # a retry: the stored answer wins
    if test.status != "in_progress":
        raise rules.AssessError(409, "The test is already finished")
    if test.session_id is not None:
        session = db.get(StudySession, test.session_id)
        if session is None or session.state != "running":
            raise rules.AssessError(409, "Session is not running")
    if position != test.current_index:
        raise rules.AssessError(409, "Answer the current question first")
    # Compare-and-swap so a double tap can't advance twice.
    result = db.execute(
        update(StudyTest)
        .where(
            StudyTest.id == test.id,
            StudyTest.current_index == position,
            StudyTest.status == "in_progress",
        )
        .values(current_index=position + 1)
    )
    if result.rowcount == 0:
        db.rollback()
        db.refresh(question)
        if question.answer_index is not None:
            return AnswerResult(question, False)
        raise rules.AssessError(409, "The test changed. Try again.")
    question.answer_index = answer_index
    question.answered_at = clock.now()
    total = len(questions_of(db, test.id))
    finished = position + 1 == total
    if finished:
        db.refresh(test)
        if test.graded:
            _grade(db, settings, clock, test)
        else:
            _finish_ungraded(db, clock, test)
    db.commit()
    db.refresh(test)
    return AnswerResult(question, finished)


def _grade(db: Session, settings: Settings, clock: Clock, test: StudyTest) -> None:
    db.flush()
    questions = questions_of(db, test.id)
    total = len(questions)
    right = sum(q.answer_index == q.correct_index for q in questions)
    test.score_pct = rules.score_pct(right, total)
    test.band = rules.band_for(test.score_pct, settings.grade_bands)
    test.status = "done"
    test.finished_at = clock.now()
    row = db.get(StudySession, test.session_id) if test.session_id else None
    if row is not None:
        amount = test_points(right, double_points=test.kind == "surprise")
        if amount > 0:
            db.add(Points(session_id=row.id, reason="test", amount=amount))
        if row.plan_json:
            plan = json.loads(row.plan_json)
            step = next((s for s in plan["steps"] if s["key"] == TEST_STEP), None)
            if step is not None and step["status"] == "pending":
                new = set_step_status(plan, TEST_STEP, "done")
                if not plan_service.save_plan(db, row.id, row.plan_json, new):
                    raise rules.AssessError(409, "The session changed. Try again.")
        family = db.get(Family, FAMILY_ID)
        if family is not None:
            topic = plan_service.session_topic(db, row.id)
            studied = (
                int((clock.now() - row.started_at).total_seconds() // 60)
                if row.started_at
                else 0
            )
            enqueue(
                db,
                templates.grade(
                    family.child_name,
                    test.kind,
                    topic or "today's material",
                    test.score_pct,
                    test.band,
                    right,
                    total,
                    studied,
                ),
            )


def _finish_ungraded(db: Session, clock: Clock, test: StudyTest) -> None:
    db.flush()
    questions = questions_of(db, test.id)
    right = sum(q.answer_index == q.correct_index for q in questions)
    test.score_pct = rules.score_pct(right, len(questions))  # history only: no band
    test.status = "done"
    test.finished_at = clock.now()
    row = db.get(StudySession, test.session_id) if test.session_id else None
    if row is None:
        return
    amount = challenge_rules.challenge_points(right)
    if amount > 0:
        db.add(Points(session_id=row.id, reason=test.kind, amount=amount))
    if test.kind == "warmup" and row.plan_json:
        plan = json.loads(row.plan_json)
        step = next((s for s in plan["steps"] if s["key"] == "warmup"), None)
        if step is not None and step["status"] == "pending":
            new = set_step_status(plan, "warmup", "done")
            if not plan_service.save_plan(db, row.id, row.plan_json, new):
                raise rules.AssessError(409, "The session changed. Try again.")
