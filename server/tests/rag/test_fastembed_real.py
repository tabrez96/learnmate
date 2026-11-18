import os

import numpy as np
import pytest

from learnmate.config import Settings
from learnmate.rag.embed import FastEmbedder, encode


@pytest.mark.skipif(
    "EMBED_CACHE_DIR" not in os.environ,
    reason="downloads the real model; set EMBED_CACHE_DIR to run",
)
def test_real_model_embeds_normalised():
    s = Settings()
    blobs = encode(
        FastEmbedder(s.embed_model, s.embed_cache_dir),
        ["Water evaporates.", "Soil is a mix."],
    )
    assert len(blobs) == 2
    assert len(blobs[0]) == len(blobs[1]) > 0
    for blob in blobs:
        assert abs(np.linalg.norm(np.frombuffer(blob, np.float32)) - 1) < 1e-5
    assert blobs[0] != blobs[1]
