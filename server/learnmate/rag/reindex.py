"""Re-embeds chunks with the configured model: all of them (the command) or only stale ones (start-up)."""

import logging

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from learnmate.clock import SystemClock
from learnmate.config import get_settings
from learnmate.db import create_db_engine, make_session_factory
from learnmate.models import Chapter, Chunk, Material, Subject
from learnmate.rag.embed import Embedder, embed_input, encode, make_embedder

BATCH = 64


def reindex(
    session_factory: sessionmaker[Session], embedder: Embedder, *, only_stale: bool
) -> int:
    """Returns how many chunks were re-embedded. Commits per batch, so an interrupted run resumes at start-up."""
    query = select(Chunk.id).order_by(Chunk.id)
    if only_stale:
        query = query.where(
            or_(
                Chunk.embed_model.is_(None),
                Chunk.embed_model != embedder.model,
                Chunk.embedding.is_(None),
            )
        )
    with session_factory() as db:
        ids = list(db.scalars(query))

    done = 0
    for start in range(0, len(ids), BATCH):
        batch = ids[start : start + BATCH]
        with session_factory() as db:
            rows = db.execute(
                select(Chunk.id, Chunk.text, Subject.name, Material.title, Chapter.name)
                .join(Material, Chunk.material_id == Material.id)
                .join(Subject, Material.subject_id == Subject.id)
                .outerjoin(Chapter, Chunk.chapter_id == Chapter.id)
                .where(Chunk.id.in_(batch))
            ).all()
            blobs = encode(
                embedder,
                [embed_input(s, t, c, body) for _, body, s, t, c in rows],
            )
            # Only write while the row still holds the text that was embedded: a
            # deleted chunk, or an id reused by a new one, matches nothing.
            for (chunk_id, body, *_), blob in zip(rows, blobs, strict=True):
                result = db.execute(
                    update(Chunk)
                    .where(Chunk.id == chunk_id, Chunk.text == body)
                    .values(embedding=blob, embed_model=embedder.model)
                )
                done += result.rowcount
            db.commit()
    if done > 0:
        logging.getLogger(__name__).info(
            "re-embedded %d chunks with %s", done, embedder.model
        )
    return done


def main() -> None:
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    sessions = make_session_factory(engine, SystemClock())
    embedder = make_embedder(settings)
    n = reindex(sessions, embedder, only_stale=False)
    print(f"Re-embedded {n} chunks with {embedder.model}")
    engine.dispose()


if __name__ == "__main__":
    main()
