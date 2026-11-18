"""The background job that reads a material: page texts, progress, chapters, chunks, ready or failed."""

import datetime as dt
import logging
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.files import resolve_stored
from learnmate.ingest.chapters import clean, given_names, page_chapters
from learnmate.ingest.readers import (
    IMAGE_MEDIA_TYPE,
    RawPage,
    UnreadableFile,
    count_pages,
    iter_pages,
)
from learnmate.llm.budget import REACHED_MESSAGE, BudgetReached, require_budget
from learnmate.llm.types import Llm, LlmError
from learnmate.models import Chapter, Chunk, Material, MaterialFile, MaterialPage
from learnmate.rag.chunk import PageInput, chunk_pages

CHAPTER_PREVIEW_CHARS = (
    800  # per page sent to chapter detection; headings sit at the top
)
DAMAGED_MESSAGE = (
    "Couldn't read file {n} of {total}. It may be damaged: save it again and upload it."
)
AI_DOWN_MESSAGE = (
    "Couldn't read page {page}: the AI service didn't answer. Try again later."
)
NO_TEXT_MESSAGE = "No text was found in this material."
UNEXPECTED_MESSAGE = "Something went wrong while reading this material."

type Sessions = sessionmaker[Session]


class IngestFailed(Exception):
    """The message is shown to the user."""


def page_text(llm: Llm, raw: RawPage) -> str:
    if raw.image is None:
        return raw.text
    return llm.read_page(raw.image, IMAGE_MEDIA_TYPE).value.text.strip()


def ingest(
    session_factory: Sessions,
    settings: Settings,
    material_id: int,
    *,
    llm: Llm,
    clock: Clock,
) -> None:
    # Material ids can be reused after a delete, so every write is tied to the
    # creation time of the material this job started with.
    with session_factory() as db:
        material = db.get(Material, material_id)
        if material is None or material.status != "reading":
            return
        created_at = material.created_at
    try:
        _run(session_factory, settings, material_id, created_at, llm, clock)
    except IngestFailed as exc:
        _fail(session_factory, material_id, created_at, str(exc))
    except Exception:
        logging.getLogger(__name__).exception("reading material %s failed", material_id)
        _fail(session_factory, material_id, created_at, UNEXPECTED_MESSAGE)


def _current(db: Session, material_id: int, created_at: dt.datetime) -> Material | None:
    """The material this job started with, or None if it was deleted or its id reused."""
    material = db.get(Material, material_id)
    if material is None or material.created_at != created_at:
        return None
    return material


def _check_budget(session_factory: Sessions, settings: Settings, clock: Clock) -> None:
    with session_factory() as db:
        try:
            require_budget(db, settings, clock)
        except BudgetReached as exc:
            raise IngestFailed(REACHED_MESSAGE) from exc


def _run(
    session_factory: Sessions,
    settings: Settings,
    material_id: int,
    created_at: dt.datetime,
    llm: Llm,
    clock: Clock,
) -> None:
    with session_factory() as db:
        material = _current(db, material_id, created_at)
        if material is None:
            return
        hint = material.chapters_hint
        title = material.title
        sources: list[tuple[Path, str]] = [
            (resolve_stored(settings.data_dir, f.path), f.mime)
            for f in db.scalars(
                select(MaterialFile)
                .where(MaterialFile.material_id == material_id)
                .order_by(MaterialFile.id)
            )
        ]

    _check_budget(session_factory, settings, clock)

    total = 0
    for n, (path, mime) in enumerate(sources, start=1):
        try:
            total += count_pages(path, mime)
        except UnreadableFile as exc:
            raise IngestFailed(_damaged(n, len(sources))) from exc
    with session_factory() as db:
        material = _current(db, material_id, created_at)
        if material is None:
            return
        material.pages_total = total
        db.commit()

    texts: list[str] = []
    for n, (path, mime) in enumerate(sources, start=1):
        try:
            for raw in iter_pages(path, mime):
                page = len(texts) + 1
                if raw.image is not None:
                    _check_budget(session_factory, settings, clock)
                try:
                    text = page_text(llm, raw)
                except LlmError as exc:
                    raise IngestFailed(AI_DOWN_MESSAGE.format(page=page)) from exc
                with session_factory() as db:
                    material = _current(db, material_id, created_at)
                    if material is None:
                        return
                    db.add(MaterialPage(material_id=material_id, page=page, text=text))
                    material.pages_read = page
                    db.commit()
                texts.append(text)
        except UnreadableFile as exc:
            raise IngestFailed(_damaged(n, len(sources))) from exc

    if not any(t.strip() for t in texts):
        raise IngestFailed(NO_TEXT_MESSAGE)

    _check_budget(session_factory, settings, clock)
    try:
        previews = [t[:CHAPTER_PREVIEW_CHARS] for t in texts]
        guesses = llm.detect_chapters(previews, hint=hint).value.chapters
    except LlmError as exc:
        raise IngestFailed(UNEXPECTED_MESSAGE) from exc
    chapters = clean(guesses, len(texts), given=given_names(hint), fallback=title)

    with session_factory() as db:
        material = _current(db, material_id, created_at)
        if material is None:
            return
        rows = [
            Chapter(material_id=material_id, name=c.name, position=i)
            for i, c in enumerate(chapters, start=1)
        ]
        db.add_all(rows)
        db.flush()
        owner = page_chapters([c.start_page for c in chapters], len(texts))
        pages = db.scalars(
            select(MaterialPage).where(MaterialPage.material_id == material_id)
        )
        for row in pages:
            row.chapter_id = rows[owner[row.page - 1]].id
        drafts = chunk_pages(
            [
                PageInput(page=i + 1, chapter=owner[i], text=t)
                for i, t in enumerate(texts)
            ]
        )
        db.add_all(
            Chunk(
                material_id=material_id,
                chapter_id=rows[d.chapter].id,
                page=d.page,
                position=d.position,
                text=d.text,
            )
            for d in drafts
        )
        material.status = "ready"
        material.error = None
        db.commit()


def _damaged(n: int, total: int) -> str:
    return DAMAGED_MESSAGE.format(n=n, total=total)


def _fail(
    session_factory: Sessions, material_id: int, created_at: dt.datetime, message: str
) -> None:
    with session_factory() as db:
        material = _current(db, material_id, created_at)
        if material is None:
            return
        db.execute(delete(Chunk).where(Chunk.material_id == material_id))
        db.execute(delete(MaterialPage).where(MaterialPage.material_id == material_id))
        db.execute(delete(Chapter).where(Chapter.material_id == material_id))
        material.status = "failed"
        material.error = message
        db.commit()
