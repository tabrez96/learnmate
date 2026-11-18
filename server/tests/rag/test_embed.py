import numpy as np

from learnmate.config import Settings
from learnmate.rag.embed import (
    FastEmbedder,
    embed_input,
    encode,
    make_embedder,
    to_blobs,
)
from learnmate.rag.fake_embed import FakeEmbedder


def test_embed_input_with_chapter():
    assert (
        embed_input("Science", "Unit", "The Water Cycle", "Rain falls.")
        == "Science / Unit / The Water Cycle\n\nRain falls."
    )


def test_embed_input_without_chapter():
    assert embed_input("Science", "Unit", None, "Rain falls.") == (
        "Science / Unit\n\nRain falls."
    )


def test_to_blobs_normalises_float32():
    blobs = to_blobs(np.array([[3.0, 4.0, 0.0], [1.0, 1.0, 1.0]]))
    assert len(blobs) == 2
    expected = [[0.6, 0.8, 0.0], [1 / np.sqrt(3)] * 3]
    for blob, want in zip(blobs, expected, strict=True):
        vector = np.frombuffer(blob, np.float32)
        assert len(vector) == 3
        assert abs(np.linalg.norm(vector) - 1) < 1e-5
        assert np.allclose(vector, want, atol=1e-5)


def test_to_blobs_keeps_zero_row():
    (blob,) = to_blobs(np.zeros((1, 4)))
    assert list(np.frombuffer(blob, np.float32)) == [0.0] * 4


def test_encode_empty_skips_model():
    embedder = FakeEmbedder("fake")
    assert encode(embedder, []) == []
    assert embedder.calls == []


def test_make_embedder_uses_setting():
    fake = make_embedder(Settings(embed_provider="fake", embed_model="fake-m"))
    assert isinstance(fake, FakeEmbedder)
    assert fake.model == "fake-m"
    real = make_embedder(Settings(embed_provider="fastembed", embed_model="some/model"))
    assert isinstance(real, FastEmbedder)
    assert real.model == "some/model"
    assert real._impl is None


def test_fake_embedder_dimension_and_determinism():
    for dim in (4, 12):
        out = FakeEmbedder("m", dim=dim).embed(["a", "b"])
        assert out.shape == (2, dim)
    embedder = FakeEmbedder("m", dim=4)
    assert (embedder.embed(["a"]) == embedder.embed(["a"])).all()
