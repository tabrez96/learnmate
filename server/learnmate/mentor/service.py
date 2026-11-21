"""Database glue for the mentor lesson."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.budget import require_budget
from learnmate.llm.types import Lesson, Llm, LlmError, Passage
from learnmate.mentor.lesson import (
    ChapterKey,
    MentorError,
    Retrieve,
    ScopeChunk,
    answer_check,
    citations_valid,
    lesson_entry,
    lesson_step,
    select_passages,
    with_lesson,
)
from learnmate.models import Chapter, Chunk, Family, Material, Points, StudySession
from learnmate.plan import service as plan_service
from learnmate.plan.progress import QUICK_CHECK_POINTS
from learnmate.rag.embed import Embedder
from learnmate.rag.search import Scope, search
from learnmate.sessions import service as sessions


def _scope_chunks(db: Session, row: StudySession) -> list[ScopeChunk]:
    materials, chapters = sessions.scope_ids(db, row)
    query = (
        select(Chunk, Material.title, Chapter.name)
        .join(Material, Chunk.material_id == Material.id)
        .outerjoin(Chapter, Chunk.chapter_id == Chapter.id)
    )
    query = query.where(Chunk.kind == "text")
    if chapters:
        query = query.where(Chunk.chapter_id.in_(chapters))
    else:
        query = query.where(Chunk.material_id.in_(materials))
    # Position grows across a whole material in page order: chapter and page order.
    query = query.order_by(Chunk.material_id, Chunk.position)
    return [
        ScopeChunk(
            id=chunk.id,
            material_id=chunk.material_id,
            chapter_id=chunk.chapter_id,
            material=title,
            chapter=name or "",
            page=chunk.page,
            position=chunk.position,
            text=chunk.text,
        )
        for chunk, title, name in db.execute(query)
    ]


def _retriever(db: Session, settings: Settings, embedder: Embedder) -> Retrieve:
    def retrieve(key: ChapterKey, query: str) -> list[int]:
        material_id, chapter_id = key
        scope = (
            Scope.chapters([chapter_id])
            if chapter_id is not None
            else Scope.materials([material_id])
        )
        hits = search(
            db, embedder, scope, query, min_similarity=settings.rag_min_similarity
        )
        return hits[0].chunk_ids if hits else []

    return retrieve


def _running(db: Session, session_id: int) -> StudySession:
    row = db.get(StudySession, session_id)
    if row is None:
        raise MentorError(404, "Session not found")
    if row.state != "running":
        raise MentorError(409, "Session is not running")
    return row


def _build(llm: Llm, topic: str, passages: list[Passage], grade: int) -> Lesson:
    sent = {p.id for p in passages}
    try:
        for _ in range(2):
            lesson = llm.build_lesson(topic, passages=passages, grade=grade).value
            if citations_valid(lesson, sent):
                return lesson
    except LlmError as e:
        # Usage is already recorded by the metering wrapper.
        raise MentorError(502, "The mentor couldn't make the lesson. Try again.") from e
    raise MentorError(502, "The lesson couldn't be made from your material. Try again.")


def start_lesson(
    db: Session,
    settings: Settings,
    clock: Clock,
    llm: Llm,
    embedder: Embedder,
    session_id: int,
) -> dict:
    row = _running(db, session_id)
    plan = plan_service.get_plan(db, settings, clock, session_id)
    step = lesson_step(plan)
    if "lesson" in step:
        return plan
    require_budget(db, settings, clock)
    family = db.get(Family, FAMILY_ID)
    if family is None:
        raise MentorError(409, "Family not set up")
    passages = select_passages(
        _scope_chunks(db, row), _retriever(db, settings, embedder)
    )
    if not passages:
        raise MentorError(422, "There's no material to teach from yet")
    topic = step.get("topic") or "today's topic"
    lesson = _build(llm, topic, passages, family.grade)
    for _ in range(2):
        db.refresh(row)
        old_json = row.plan_json
        current = json.loads(old_json)
        if "lesson" in lesson_step(current):
            return current  # a parallel request won
        new = with_lesson(current, lesson_entry(lesson, passages))
        if plan_service.save_plan(db, row.id, old_json, new):
            db.commit()
            return new
        db.rollback()
    raise MentorError(409, "The session changed. Try again.")


def answer(
    db: Session,
    settings: Settings,
    clock: Clock,
    session_id: int,
    index: int,
    answer_index: int,
) -> tuple[dict, bool]:
    for _ in range(2):
        row = _running(db, session_id)
        db.refresh(row)
        plan = plan_service.get_plan(db, settings, clock, session_id)
        new, correct = answer_check(plan, index, answer_index)
        if plan_service.save_plan(db, session_id, row.plan_json, new):
            if correct:
                db.add(
                    Points(
                        session_id=session_id,
                        reason="quick_check",
                        amount=QUICK_CHECK_POINTS,
                    )
                )
            db.commit()
            return new, correct
        db.rollback()
    raise MentorError(409, "The session changed. Try again.")
