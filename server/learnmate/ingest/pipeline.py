"""The background job that reads a material: page texts, progress, chapters, chunks, ready or failed."""

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.files import resolve_stored
from learnmate.ingest.chapters import clean, given_names, page_chapters
from learnmate.ingest.figures import (
    figure_path,
    find_figures,
    generation_stamp,
    remove_figure_files,
    save_crop,
)
from learnmate.ingest.readers import (
    IMAGE_MEDIA_TYPE,
    RawPage,
    UnreadableFile,
    count_pages,
    iter_pages,
)
from learnmate.llm.budget import REACHED_MESSAGE, BudgetReached, require_budget
from learnmate.llm.types import Llm, LlmError
from learnmate.models import (
    Chapter,
    Chunk,
    Figure,
    Material,
    MaterialFile,
    MaterialPage,
    Subject,
)
from learnmate.rag.chunk import ChunkDraft, PageInput, chunk_pages
from learnmate.rag.embed import Embedder, embed_input, encode

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


@dataclass(frozen=True)
class FigureDraft:
    page: int
    description: str
    path: str


class IngestFailed(Exception):
    """The message is shown to the user."""


def page_text(llm: Llm, raw: RawPage) -> str:
    if raw.image is None:
        return raw.text
    return llm.read_page(raw.image, IMAGE_MEDIA_TYPE).value.text.strip()


def embedded_chunks(
    embedder: Embedder,
    subject: str,
    title: str,
    chapter_names: list[str],
    starts: list[int],
    texts: list[str],
) -> tuple[list[int], list[tuple[ChunkDraft, bytes]]]:
    """Page owners (0-based chapter per page) and each chunk with its embedding."""
    owner = page_chapters(starts, len(texts))
    drafts = chunk_pages(
        [PageInput(page=i + 1, chapter=owner[i], text=t) for i, t in enumerate(texts)]
    )
    blobs = encode(
        embedder,
        [embed_input(subject, title, chapter_names[d.chapter], d.text) for d in drafts],
    )
    return owner, list(zip(drafts, blobs, strict=True))


def ingest(
    session_factory: Sessions,
    settings: Settings,
    material_id: int,
    *,
    llm: Llm,
    embedder: Embedder,
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
        _run(session_factory, settings, material_id, created_at, llm, embedder, clock)
    except IngestFailed as exc:
        _fail(session_factory, settings, material_id, created_at, str(exc))
    except Exception:
        logging.getLogger(__name__).exception("reading material %s failed", material_id)
        _fail(session_factory, settings, material_id, created_at, UNEXPECTED_MESSAGE)


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
    embedder: Embedder,
    clock: Clock,
) -> None:
    with session_factory() as db:
        material = _current(db, material_id, created_at)
        if material is None:
            return
        hint = material.chapters_hint
        title = material.title
        subject_name = db.get(Subject, material.subject_id).name
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

    stamp = generation_stamp(created_at)
    texts: list[str] = []
    figures: list[FigureDraft] = []
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
                if raw.image is not None:
                    _check_budget(session_factory, settings, clock)
                    for i, crop in enumerate(find_figures(llm, raw.image), start=1):
                        rel = figure_path(material_id, stamp, page, i)
                        if save_crop(settings.data_dir, rel, crop.png):
                            figures.append(FigureDraft(page, crop.description, rel))
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

    chapter_names = [c.name for c in chapters]
    owner, embedded = embedded_chunks(
        embedder,
        subject_name,
        title,
        chapter_names,
        [c.start_page for c in chapters],
        texts,
    )
    figure_blobs = encode(
        embedder,
        [
            embed_input(
                subject_name, title, chapter_names[owner[f.page - 1]], f.description
            )
            for f in figures
        ],
    )

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
        pages = db.scalars(
            select(MaterialPage).where(MaterialPage.material_id == material_id)
        )
        for row in pages:
            row.chapter_id = rows[owner[row.page - 1]].id
        db.add_all(
            Chunk(
                material_id=material_id,
                chapter_id=rows[d.chapter].id,
                page=d.page,
                position=d.position,
                text=d.text,
                embedding=blob,
                embed_model=embedder.model,
            )
            for d, blob in embedded
        )
        next_position = max((d.position for d, _ in embedded), default=-1) + 1
        for i, (f, blob) in enumerate(zip(figures, figure_blobs, strict=True)):
            chapter_id = rows[owner[f.page - 1]].id
            figure = Figure(
                material_id=material_id,
                chapter_id=chapter_id,
                page=f.page,
                path=f.path,
                description=f.description,
            )
            db.add(figure)
            db.flush()
            db.add(
                Chunk(
                    material_id=material_id,
                    chapter_id=chapter_id,
                    page=f.page,
                    position=next_position + i,
                    kind="figure",
                    figure_id=figure.id,
                    text=f.description,
                    embedding=blob,
                    embed_model=embedder.model,
                )
            )
        material.status = "ready"
        material.error = None
        db.commit()


def _damaged(n: int, total: int) -> str:
    return DAMAGED_MESSAGE.format(n=n, total=total)


def _fail(
    session_factory: Sessions,
    settings: Settings,
    material_id: int,
    created_at: dt.datetime,
    message: str,
) -> None:
    with session_factory() as db:
        material = _current(db, material_id, created_at)
        if material is None:
            return
        db.execute(delete(Chunk).where(Chunk.material_id == material_id))
        db.execute(delete(Figure).where(Figure.material_id == material_id))
        db.execute(delete(MaterialPage).where(MaterialPage.material_id == material_id))
        db.execute(delete(Chapter).where(Chapter.material_id == material_id))
        material.status = "failed"
        material.error = message
        db.commit()
    remove_figure_files(settings.data_dir, material_id, generation_stamp(created_at))
