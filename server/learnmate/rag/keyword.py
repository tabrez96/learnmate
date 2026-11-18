"""Keyword (BM25) search over chunk_fts, limited to given chapters or materials."""

import re

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

_SEARCH = """
    SELECT chunk.id, bm25(chunk_fts) AS rank
    FROM chunk_fts JOIN chunk ON chunk.id = chunk_fts.rowid
    WHERE chunk_fts MATCH :q AND chunk.{column} IN :ids
    ORDER BY rank, chunk.id
    LIMIT :limit
    """
_SEARCH_CHAPTERS = text(_SEARCH.format(column="chapter_id")).bindparams(
    bindparam("ids", expanding=True)
)
_SEARCH_MATERIALS = text(_SEARCH.format(column="material_id")).bindparams(
    bindparam("ids", expanding=True)
)


def fts_query(text: str) -> str | None:
    """Each word quoted and OR-ed, so user text can't break FTS5 syntax; None if no words."""
    words = re.findall(r"[^\W_]+", text.lower())
    if not words:
        return None
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words))


def keyword_search(
    db: Session,
    text: str,
    *,
    chapter_ids: list[int] | None = None,
    material_ids: list[int] | None = None,
    limit: int = 20,
) -> list[tuple[int, float]]:
    """(chunk id, score) best first; a higher score is a better match."""
    if (chapter_ids is None) == (material_ids is None):
        raise ValueError("give chapter_ids or material_ids")
    statement = _SEARCH_CHAPTERS if chapter_ids is not None else _SEARCH_MATERIALS
    ids = chapter_ids if chapter_ids is not None else material_ids
    query = fts_query(text)
    if query is None or not ids:
        return []
    rows = db.execute(statement, {"q": query, "ids": ids, "limit": limit})
    return [(row.id, -row.rank) for row in rows]
