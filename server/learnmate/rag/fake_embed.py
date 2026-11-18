"""A deterministic embedder of any dimension, for tests and offline runs."""

import hashlib

import numpy as np


class FakeEmbedder:
    def __init__(self, model: str, dim: int = 8) -> None:
        self.model = model
        self.dim = dim
        self.calls: list[list[str]] = []  # every batch it was asked to embed

    def embed(self, texts: list[str]) -> np.ndarray:
        self.calls.append(list(texts))
        rows = []
        for t in texts:
            digest = hashlib.sha256(t.encode()).digest()
            raw = (digest * (self.dim // len(digest) + 1))[: self.dim]
            rows.append([b - 127.5 for b in raw])  # deliberately not normalised
        return np.array(rows, dtype=np.float64).reshape(len(texts), self.dim)
