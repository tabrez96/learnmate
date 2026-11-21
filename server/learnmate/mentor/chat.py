"""Database glue for the mentor chat."""

import json
from typing import Literal
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.budget import require_budget
from learnmate.llm.types import Llm, LlmError, Passage, Turn
from learnmate.mentor.answers import (
    HISTORY_TURNS,
    NOT_COVERED_TEXT,
    answer_from_books,
    retrieval_record,
    source_lines,
)
from learnmate.mentor.lesson import MentorError
from learnmate.mentor.visual import VisualError, parse_visual
from learnmate.models import Chapter, Family, Material, Message, StudySession
from learnmate.rag.embed import Embedder
from learnmate.rag.search import Reranker, Scope, SearchHit, search, search_query
from learnmate.sessions import service as sessions


def _session(db: Session, session_id: int) -> StudySession:
    row = db.get(StudySession, session_id)
    if row is None:
        raise MentorError(404, "Session not found")
    return row


def _history(db: Session, session_id: int) -> list[Turn]:
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(HISTORY_TURNS)
    ).all()
    return [Turn(role=m.role, text=m.text) for m in reversed(rows)]


def _scope(db: Session, row: StudySession) -> Scope:
    materials, chapters = sessions.scope_ids(db, row)
    return Scope.chapters(chapters) if chapters else Scope.materials(materials)


def _passages(db: Session, hits: list[SearchHit]) -> dict[int, Passage]:
    material_ids = {h.material_id for h in hits}
    chapter_ids = {h.chapter_id for h in hits if h.chapter_id is not None}
    titles = {
        i: t
        for i, t in db.execute(
            select(Material.id, Material.title).where(Material.id.in_(material_ids))
        )
    }
    names = {
        i: n
        for i, n in db.execute(
            select(Chapter.id, Chapter.name).where(Chapter.id.in_(chapter_ids))
        )
    }
    return {
        h.id: Passage(
            id=h.id,
            text=h.text,
            material=titles.get(h.material_id, ""),
            chapter=names.get(h.chapter_id, ""),
            page=h.page,
        )
        for h in hits
    }


def _books_message(
    db: Session,
    settings: Settings,
    llm: Llm,
    embedder: Embedder,
    reranker: Reranker,
    row: StudySession,
    family: Family,
    text: str,
    history: list[Turn],
) -> Message:
    query = search_query(llm, text, history)
    hits = search(
        db,
        embedder,
        _scope(db, row),
        query,
        rerank=reranker,
        min_similarity=settings.rag_min_similarity,
    )
    passages = _passages(db, hits)
    result = None
    attempts = 0
    if hits:
        result = answer_from_books(
            lambda: (
                llm.answer_from_passages(
                    text,
                    history=history,
                    passages=list(passages.values()),
                    grade=family.grade,
                ).value
            ),
            set(passages),
        )
        attempts = result.attempts
    record = retrieval_record(
        mode="books",
        query=query,
        rerank=settings.rerank_enabled,
        hits=hits,
        covered=bool(result and result.answer),
        attempts=attempts,
    )
    if result is None or result.answer is None:
        return Message(
            session_id=row.id,
            role="mentor",
            text=NOT_COVERED_TEXT,
            sources_json="[]",
            retrieval_json=json.dumps(record),
        )
    return Message(
        session_id=row.id,
        role="mentor",
        text=result.answer.text,
        sources_json=json.dumps(source_lines(result.answer.passage_ids, passages)),
        visual_json=json.dumps(result.visual) if result.visual else None,
        retrieval_json=json.dumps(record),
    )


def _is_web_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return parts.scheme in ("http", "https") and bool(parts.hostname)
    except ValueError:
        return False


def _outside_message(
    settings: Settings,
    llm: Llm,
    row: StudySession,
    family: Family,
    text: str,
    history: list[Turn],
) -> Message:
    answer = llm.answer_outside(text, history=history, grade=family.grade).value
    if not _is_web_url(answer.source_url) or not answer.text.strip():
        raise MentorError(
            502, "The mentor couldn't check outside the books. Try again."
        )
    try:
        visual = parse_visual(answer.visual)
    except VisualError:
        visual = None
    record = retrieval_record(
        mode="outside",
        query=text,
        rerank=settings.rerank_enabled,
        hits=[],
        covered=True,
        attempts=1,
    )
    return Message(
        session_id=row.id,
        role="mentor",
        text=answer.text,
        sources_json="[]",
        visual_json=json.dumps(visual) if visual else None,
        outside=True,
        outside_source_url=answer.source_url,
        retrieval_json=json.dumps(record),
    )


def post_message(
    db: Session,
    settings: Settings,
    clock: Clock,
    llm: Llm,
    embedder: Embedder,
    reranker: Reranker,
    session_id: int,
    text: str,
    mode: Literal["books", "outside"],
) -> tuple[Message, Message]:
    row = _session(db, session_id)
    if row.state != "running":
        raise MentorError(409, "Session is not running")
    family = db.get(Family, FAMILY_ID)
    if family is None:
        raise MentorError(409, "Family not set up")
    if mode == "outside" and not family.outside_books_allowed:
        raise MentorError(403, "Checking outside the books is switched off")
    require_budget(db, settings, clock)
    history = _history(db, session_id)
    try:
        if mode == "books":
            mentor = _books_message(
                db, settings, llm, embedder, reranker, row, family, text, history
            )
        else:
            mentor = _outside_message(settings, llm, row, family, text, history)
    except LlmError as e:
        # Usage is already recorded by the metering wrapper.
        raise MentorError(502, "The mentor couldn't answer. Try again.") from e
    student = Message(session_id=session_id, role="student", text=text)
    db.add(student)
    db.flush()  # the student's question gets the lower id
    db.add(mentor)
    db.commit()
    return student, mentor


def list_messages(db: Session, session_id: int) -> list[Message]:
    _session(db, session_id)
    return list(
        db.scalars(
            select(Message).where(Message.session_id == session_id).order_by(Message.id)
        )
    )


def can_check_outside(message: Message, family: Family | None) -> bool:
    if family is None or not family.outside_books_allowed:
        return False
    if message.role != "mentor" or message.outside:
        return False
    return json.loads(message.retrieval_json or "{}").get("covered") is False
