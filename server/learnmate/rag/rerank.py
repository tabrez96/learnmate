"""Local cross-encoder rerank of the fused candidates, behind RERANK_ENABLED."""

import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from fastembed.rerank.cross_encoder import TextCrossEncoder

from learnmate.config import Settings
from learnmate.rag.search import Candidate, Reranker, no_rerank

RERANK_MAX_SECONDS = 1.5  # per question, the whole search, on the server's CPU

type Scorer = Callable[[str, list[str]], list[float]]


class FastCrossEncoder:
    """Scores (query, text) pairs; the model loads on first use."""

    def __init__(self, model: str, cache_dir: Path | None) -> None:
        self.model = model
        self._cache_dir = cache_dir
        self._impl: TextCrossEncoder | None = None
        self._lock = threading.Lock()

    def __call__(self, query: str, texts: list[str]) -> list[float]:
        with self._lock:
            if self._impl is None:
                self._impl = TextCrossEncoder(
                    model_name=self.model,
                    cache_dir=str(self._cache_dir) if self._cache_dir else None,
                )
            return [float(s) for s in self._impl.rerank(query, texts, batch_size=32)]


def cross_encoder_rerank(score: Scorer) -> Reranker:
    """A reranker that replaces each candidate's score with the cross-encoder's, best first, ties by id."""

    def rerank(query: str, candidates: list[Candidate]) -> list[Candidate]:
        if not candidates:
            return []
        scores = score(query, [c.text for c in candidates])
        rescored = [
            replace(c, score=s) for c, s in zip(candidates, scores, strict=True)
        ]
        return sorted(rescored, key=lambda c: (-c.score, c.id))

    return rerank


def make_reranker(settings: Settings) -> Reranker:
    if not settings.rerank_enabled:
        return no_rerank
    return cross_encoder_rerank(
        FastCrossEncoder(settings.rerank_model, settings.embed_cache_dir)
    )
