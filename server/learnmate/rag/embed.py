"""Dense embeddings of chunk text; the model comes only from settings."""

import threading
from pathlib import Path
from typing import Protocol

import numpy as np
from fastembed import TextEmbedding

from learnmate.config import Settings
from learnmate.rag.fake_embed import FakeEmbedder


class Embedder(Protocol):
    model: str  # stored in chunk.embed_model

    def embed(self, texts: list[str]) -> np.ndarray:
        """Shape (len(texts), dim), any float dtype."""
        ...


def embed_input(subject: str, title: str, chapter: str | None, text: str) -> str:
    """'<subject> / <material title> / <chapter>' then a blank line then the chunk text."""
    parts = [subject, title] + ([chapter] if chapter else [])
    return " / ".join(parts) + "\n\n" + text


def to_blobs(vectors: np.ndarray) -> list[bytes]:
    """Each row L2-normalised and stored as float32 bytes; an all-zero row stays zero."""
    v = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    v = np.divide(v, norms, out=np.zeros_like(v), where=norms > 0)
    return [row.tobytes() for row in v]


def encode(embedder: Embedder, texts: list[str]) -> list[bytes]:
    if not texts:
        return []
    return to_blobs(embedder.embed(texts))


class FastEmbedder:
    def __init__(self, model: str, cache_dir: Path | None) -> None:
        self.model = model
        self._cache_dir = cache_dir
        self._impl: TextEmbedding | None = None
        self._lock = threading.Lock()

    def embed(self, texts: list[str]) -> np.ndarray:
        with self._lock:  # load once; ingest runs in worker threads
            if self._impl is None:
                self._impl = TextEmbedding(
                    model_name=self.model,
                    cache_dir=str(self._cache_dir) if self._cache_dir else None,
                )
            return np.stack(list(self._impl.embed(texts, batch_size=32)))


def make_embedder(settings: Settings) -> Embedder:
    if settings.embed_provider == "fake":
        return FakeEmbedder(settings.embed_model)
    return FastEmbedder(settings.embed_model, settings.embed_cache_dir)
