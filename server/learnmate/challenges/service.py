"""Database glue for the warm-up, the short challenge and the bonus challenge."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.assess import rules as assess_rules
from learnmate.assess import service as assess_service
from learnmate.challenges import rules
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.types import Llm
from learnmate.mentor import service as mentor_service
from learnmate.mentor.lesson import ScopeChunk, select_passages
from learnmate.models import (
    Chapter,
    Chunk,
    Family,
    Material,
    SessionChapter,
    SessionMaterial,
    StudySession,
    StudyTest,
)
from learnmate.plan import service as plan_service
from learnmate.plan.rules import TEST_STEP
from learnmate.rag.embed import Embedder
from learnmate.sessions import service as sessions


def _scope_chunk(chunk: Chunk, title: str, name: str | None) -> ScopeChunk:
    return ScopeChunk(
        id=chunk.id,
        material_id=chunk.material_id,
        chapter_id=chunk.chapter_id,
        material=title,
        chapter=name or "",
        page=chunk.page,
        position=chunk.position,
        text=chunk.text,
    )


def earlier_chunks(db: Session, row: StudySession) -> list[ScopeChunk]:
    """Text of the subject's recent earlier sessions, minus this session's own scope."""
    if row.subject_id is None or row.started_at is None:
        return []
    earlier = list(
        db.scalars(
            select(StudySession.id)
            .where(
                StudySession.subject_id == row.subject_id,
                StudySession.id != row.id,
                StudySession.state.not_in(("set_up", "cancelled")),
                StudySession.started_at.is_not(None),
                StudySession.started_at < row.started_at,
            )
            .order_by(StudySession.started_at.desc())
            .limit(rules.RECENT_SESSIONS)
        )
    )
    if not earlier:
        return []
    chapter_ids = list(
        db.scalars(
            select(SessionChapter.chapter_id).where(
                SessionChapter.session_id.in_(earlier)
            )
        )
    )
    with_chapters = select(SessionChapter.session_id)
    material_ids = list(
        db.scalars(
            select(SessionMaterial.material_id).where(
                SessionMaterial.session_id.in_(earlier),
                SessionMaterial.session_id.not_in(with_chapters),
            )
        )
    )
    materials, chapters = sessions.scope_ids(db, row)
    query = (
        select(Chunk, Material.title, Chapter.name)
        .join(Material, Chunk.material_id == Material.id)
        .outerjoin(Chapter, Chunk.chapter_id == Chapter.id)
        .where(
            Chunk.kind == "text",
            Material.subject_id == row.subject_id,
            or_(Chunk.chapter_id.in_(chapter_ids), Chunk.material_id.in_(material_ids)),
        )
    )
    if chapters:
        query = query.where(
            or_(Chunk.chapter_id.is_(None), Chunk.chapter_id.not_in(chapters))
        )
    else:
        query = query.where(Chunk.material_id.not_in(materials))
    query = query.order_by(Chunk.material_id, Chunk.position)
    return [_scope_chunk(*r) for r in db.execute(query)]


def challenge_scope(db: Session, row: StudySession) -> list[ScopeChunk]:
    return earlier_chunks(db, row) or mentor_service.scope_chunks(db, row)


def _existing(db: Session, session_id: int, kind: str) -> StudyTest | None:
    return db.scalars(
        select(StudyTest)
        .where(
            StudyTest.session_id == session_id,
            StudyTest.kind == kind,
            StudyTest.graded.is_(False),
        )
        .order_by(StudyTest.id.desc())
    ).first()


def create_challenge(
    db: Session,
    settings: Settings,
    clock: Clock,
    llm: Llm,
    embedder: Embedder,
    session_id: int,
    kind: str,
) -> StudyTest:
    row = db.get(StudySession, session_id)
    if row is None:
        raise assess_rules.AssessError(404, "Session not found")
    if row.state != "running":
        raise assess_rules.AssessError(409, "Session is not running")
    # One of each kind per session: a retry or double tap gets the same quiz.
    existing = _existing(db, session_id, kind)
    if existing is not None:
        return existing
    plan = plan_service.get_plan(db, settings, clock, session_id)
    status = {s["key"]: s["status"] for s in plan["steps"]}
    if kind == "warmup" and status.get("warmup") != "pending":
        raise assess_rules.AssessError(409, "The warm-up is already finished")
    if kind == "bonus" and status.get(TEST_STEP) != "done":
        raise assess_rules.AssessError(409, "Finish the test first")
    family = db.get(Family, FAMILY_ID)
    if family is None:
        raise assess_rules.AssessError(409, "Family not set up")
    scope = challenge_scope(db, row)
    passages = select_passages(scope, mentor_service.retriever(db, settings, embedder))
    if not passages:
        raise assess_rules.AssessError(
            422, "There's no material to make a challenge from yet"
        )
    chosen = assess_service.make_questions(
        llm, scope, passages, rules.question_count(kind), family.grade
    )
    existing = _existing(db, session_id, kind)  # a parallel request may have won
    if existing is not None:
        return existing
    test = StudyTest(
        session_id=row.id, subject_id=row.subject_id, kind=kind, graded=False
    )
    db.add(test)
    db.flush()
    assess_service.store_questions(db, test, chosen)
    db.commit()
    return test
