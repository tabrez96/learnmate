"""Mentor answers: checking citations, the one retry, source lines. Pure."""

from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Any

from learnmate.llm.types import BooksAnswer, Passage
from learnmate.mentor.visual import VisualError, parse_visual
from learnmate.rag.search import SearchHit

NOT_COVERED_TEXT = "Your books don't cover this."
HISTORY_TURNS = 6


@dataclass(frozen=True)
class BooksResult:
    answer: BooksAnswer | None  # None = the books don't cover it
    visual: dict[str, Any] | None
    attempts: int


def citations_ok(answer: BooksAnswer, retrieved: set[int]) -> bool:
    return bool(
        answer.covered
        and answer.text.strip()
        and answer.passage_ids
        and all(i in retrieved for i in answer.passage_ids)
    )


def answer_from_books(
    ask: Callable[[], BooksAnswer],
    retrieved: set[int],
    figure_ids: Collection[int] = frozenset(),
) -> BooksResult:
    """At most two calls: a bad citation or a bad visual gets one retry."""
    fallback: BooksAnswer | None = None
    for attempt in (1, 2):
        answer = ask()
        if not answer.covered:
            return BooksResult(None, None, attempt)
        if not citations_ok(answer, retrieved):
            continue
        try:
            visual = parse_visual(answer.visual, figure_ids)
        except VisualError:
            if attempt == 2:
                return BooksResult(answer, None, 2)
            fallback = answer  # text and citations are good; only the visual is not
            continue
        return BooksResult(answer, visual, attempt)
    return BooksResult(fallback, None, 2)


def source_lines(
    passage_ids: list[int], passages: dict[int, Passage]
) -> list[dict[str, Any]]:
    lines = []
    for i in dict.fromkeys(passage_ids):
        p = passages[i]
        lines.append(
            {
                "passage_id": i,
                "material": p.material,
                "chapter": p.chapter,
                "page": p.page,
            }
        )
    return lines


def retrieval_record(
    *,
    mode: str,
    query: str,
    rerank: bool,
    hits: list[SearchHit],
    covered: bool,
    attempts: int,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "query": query,
        "rerank": rerank,
        "covered": covered,
        "attempts": attempts,
        "hits": [
            {"passage_id": h.id, "chunk_ids": h.chunk_ids, "score": h.score}
            for h in hits
        ],
    }
