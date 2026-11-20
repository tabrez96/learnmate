"""Hybrid search inside a scope: BM25 plus exact cosine, fused with RRF."""

import logging
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.config import Settings
from learnmate.llm.types import Llm, LlmError, Turn
from learnmate.models import Chunk
from learnmate.rag.embed import Embedder, to_blobs
from learnmate.rag.keyword import keyword_search

log = logging.getLogger(__name__)

TOP_K = (
    20  # candidates from each of BM25 and vectors, and fused candidates kept for rerank
)
RRF_K = 60
MAX_PASSAGES = 6
MAX_CHARS = 5000  # total passage text; the first passage is always kept even if longer
MIN_SIMILARITY = Settings.model_fields[
    "rag_min_similarity"
].default  # callers pass settings.rag_min_similarity
MIN_OVERLAP = (
    20  # shortest repeated text treated as chunk overlap when joining neighbours
)


@dataclass(frozen=True)
class Scope:
    kind: Literal["chapters", "materials"]
    ids: tuple[int, ...]

    @classmethod
    def chapters(cls, ids: Iterable[int]) -> Scope:
        return cls("chapters", tuple(ids))

    @classmethod
    def materials(cls, ids: Iterable[int]) -> Scope:
        return cls("materials", tuple(ids))


@dataclass(frozen=True)
class Candidate:
    id: int
    material_id: int
    chapter_id: int | None
    page: int | None
    position: int
    text: str
    score: float  # fused RRF score, or the cross-encoder score after rerank


@dataclass(frozen=True)
class SearchHit:
    id: int  # the best-scoring chunk in the passage
    chunk_ids: list[int]  # every merged chunk, in reading (position) order
    material_id: int
    chapter_id: int | None
    page: int | None  # page of the first chunk in reading order
    text: str
    score: float  # best score among its chunks


type Reranker = Callable[[str, list[Candidate]], list[Candidate]]


def no_rerank(query: str, candidates: list[Candidate]) -> list[Candidate]:
    """The reranker when RERANK_ENABLED is off; keeps the fused order."""
    return candidates


def rrf(rankings: list[list[int]], *, k: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal rank fusion: (id, score) best first, ties by id."""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


def _scope_filter(scope: Scope):
    column = Chunk.chapter_id if scope.kind == "chapters" else Chunk.material_id
    return column.in_(scope.ids)


def vector_search(
    db: Session, embedder: Embedder, scope: Scope, query: str, *, limit: int = TOP_K
) -> tuple[list[tuple[int, float]], float | None]:
    """Top (chunk id, cosine) best first, and the best cosine (None without vectors)."""
    rows = db.execute(
        select(Chunk.id, Chunk.embedding).where(
            _scope_filter(scope),
            Chunk.embedding.is_not(None),
            Chunk.embed_model == embedder.model,
        )
    ).all()
    if not rows:
        return [], None
    q = np.frombuffer(to_blobs(embedder.embed([query]))[0], np.float32)
    matrix = np.stack([np.frombuffer(row.embedding, np.float32) for row in rows])
    sims = matrix @ q
    ranked = sorted(
        zip((row.id for row in rows), sims.tolist(), strict=True), key=_by_score
    )
    return ranked[:limit], ranked[0][1]


def _by_score(pair: tuple[int, float]) -> tuple[float, int]:
    return -pair[1], pair[0]


def below_floor(best_similarity: float | None, keyword_hits: int, floor: float) -> bool:
    return keyword_hits == 0 and (best_similarity is None or best_similarity < floor)


def _join(a: str, b: str) -> str:
    """Join neighbouring chunks, dropping the text that the chunker repeated."""
    for n in range(min(len(a), len(b)), MIN_OVERLAP - 1, -1):
        if a.endswith(b[:n]):
            rest = b[n:]
            return a + "\n" + rest.lstrip() if rest.strip() else a
    return a + "\n" + b


def _runs(cands: list[Candidate]) -> list[SearchHit]:
    groups: dict[tuple[int, int | None], list[Candidate]] = defaultdict(list)
    for c in cands:
        groups[(c.material_id, c.chapter_id)].append(c)
    hits = []
    for group in groups.values():
        group.sort(key=lambda c: c.position)
        runs: list[list[Candidate]] = []
        for c in group:
            if runs and runs[-1][-1].position + 1 == c.position:
                runs[-1].append(c)
            else:
                runs.append([c])
        for run in runs:
            best = min(run, key=lambda c: (-c.score, c.id))
            text = run[0].text
            for c in run[1:]:
                text = _join(text, c.text)
            hits.append(
                SearchHit(
                    id=best.id,
                    chunk_ids=[c.id for c in run],
                    material_id=best.material_id,
                    chapter_id=best.chapter_id,
                    page=run[0].page,
                    text=text,
                    score=best.score,
                )
            )
    return hits


def merge_neighbours(
    ranked: list[Candidate],
    *,
    max_passages: int = MAX_PASSAGES,
    max_chars: int = MAX_CHARS,
) -> list[SearchHit]:
    """Merge adjacent chunks into passages, best first, within the passage and size caps."""
    selected: list[Candidate] = []
    for c in ranked:
        tentative = selected + [c]
        runs = _runs(tentative)
        if len(runs) > max_passages:
            continue
        if selected and sum(len(h.text) for h in runs) > max_chars:
            continue
        selected = tentative
    return sorted(_runs(selected), key=lambda h: (-h.score, h.id))


def search(
    db: Session,
    embedder: Embedder,
    scope: Scope,
    query: str,
    *,
    rerank: Reranker = no_rerank,
    min_similarity: float = MIN_SIMILARITY,
) -> list[SearchHit]:
    """Up to 6 passages from inside the scope; empty when nothing is relevant."""
    if not query.strip() or not scope.ids:
        return []
    ids = list(scope.ids)
    if scope.kind == "chapters":
        keyword = keyword_search(db, query, chapter_ids=ids, limit=TOP_K)
    else:
        keyword = keyword_search(db, query, material_ids=ids, limit=TOP_K)
    vectors, best = vector_search(db, embedder, scope, query)
    if below_floor(best, len(keyword), min_similarity):
        return []
    fused = rrf([[i for i, _ in keyword], [i for i, _ in vectors]])[:TOP_K]
    rows = {
        c.id: c
        for c in db.scalars(select(Chunk).where(Chunk.id.in_([i for i, _ in fused])))
    }
    candidates = [
        Candidate(
            id=i,
            material_id=rows[i].material_id,
            chapter_id=rows[i].chapter_id,
            page=rows[i].page,
            position=rows[i].position,
            text=rows[i].text,
            score=score,
        )
        for i, score in fused
    ]
    return merge_neighbours(rerank(query, candidates))


def search_query(llm: Llm, question: str, history: list[Turn]) -> str:
    """A standalone search query: follow-ups are rewritten, first questions kept."""
    if not history:
        return question
    try:
        return llm.rewrite_query(question, history=history).value.query
    except LlmError as error:
        log.warning("query rewrite failed, searching the question as asked: %s", error)
        return question
