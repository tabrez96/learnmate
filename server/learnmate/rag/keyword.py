"""Keyword (BM25) search over chunk_fts, limited to given chapters."""

import re

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

_SEARCH = text(
    """
    SELECT chunk.id, bm25(chunk_fts) AS rank
    FROM chunk_fts JOIN chunk ON chunk.id = chunk_fts.rowid
    WHERE chunk_fts MATCH :q AND chunk.chapter_id IN :chapters
    ORDER BY rank, chunk.id
    LIMIT :limit
    """
).bindparams(bindparam("chapters", expanding=True))


def fts_query(text: str) -> str | None:
    """Each word quoted and OR-ed, so user text can't break FTS5 syntax; None if no words."""
    words = re.findall(r"[^\W_]+", text.lower())
    if not words:
        return None
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words))


def keyword_search(
    db: Session, text: str, *, chapter_ids: list[int], limit: int = 20
) -> list[tuple[int, float]]:
    """(chunk id, score) best first; a higher score is a better match."""
    query = fts_query(text)
    if query is None or not chapter_ids:
        return []
    rows = db.execute(_SEARCH, {"q": query, "chapters": chapter_ids, "limit": limit})
    return [(row.id, -row.rank) for row in rows]
