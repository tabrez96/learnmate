import os

import pytest

from learnmate.config import Settings
from learnmate.rag.rerank import FastCrossEncoder, cross_encoder_rerank, make_reranker
from learnmate.rag.search import Candidate, Scope, no_rerank, search
from tests.rag import test_search
from tests.rag.test_search import EMB, add

world = test_search.world  # the fixture, registered for this module


class FakeCrossEncoder:
    """Stands in for fastembed's TextCrossEncoder: longer text scores higher."""

    loads = 0

    def __init__(self, model_name, cache_dir=None):
        FakeCrossEncoder.loads += 1
        self.model_name = model_name

    def rerank(self, query, documents, batch_size=32):
        return iter([float(len(d)) for d in documents])


@pytest.fixture
def fake_encoder(monkeypatch):
    FakeCrossEncoder.loads = 0
    monkeypatch.setattr("learnmate.rag.rerank.TextCrossEncoder", FakeCrossEncoder)
    return FakeCrossEncoder


def candidate(id, score=0.0):
    return Candidate(id, 1, 1, 1, id, f"text {id}", score)


def test_cross_encoder_rerank_orders_by_score():
    rerank = cross_encoder_rerank(lambda query, texts: [0.1, 2.0, -1.0])
    result = rerank("q", [candidate(1), candidate(2), candidate(3)])
    assert [c.id for c in result] == [2, 1, 3]
    assert [c.score for c in result] == [2.0, 0.1, -1.0]


def test_cross_encoder_rerank_ties_by_id_and_empty():
    calls = []

    def scorer(query, texts):
        calls.append(texts)
        return [1.0] * len(texts)

    rerank = cross_encoder_rerank(scorer)
    assert [c.id for c in rerank("q", [candidate(3), candidate(1), candidate(2)])] == [
        1,
        2,
        3,
    ]
    calls.clear()
    assert rerank("q", []) == []
    assert calls == []


def test_make_reranker_off_returns_no_rerank(fake_encoder):
    assert make_reranker(Settings()) is no_rerank
    assert make_reranker(Settings(rerank_enabled=False)) is no_rerank
    assert fake_encoder.loads == 0


def test_make_reranker_on_uses_settings_model(fake_encoder):
    rerank = make_reranker(Settings(rerank_enabled=True, rerank_model="m"))
    assert fake_encoder.loads == 0
    rerank("q", [candidate(1)])
    rerank("q", [candidate(1)])
    assert fake_encoder.loads == 1


def test_fast_cross_encoder_passes_model_name(fake_encoder, tmp_path):
    scorer = FastCrossEncoder("m", tmp_path)
    assert scorer("q", ["a", "abc"]) == [1.0, 3.0]
    assert scorer.model == "m"


def test_search_with_rerank_on_reorders_and_stays_in_scope(db, world, fake_encoder):
    plants, rivers = world["plants"], world["rivers"]
    ch1, ch2, geo = world["ch1"], world["ch2"], world["geo"]
    short = add(db, plants, ch1, 1, "plant")
    long = add(db, plants, ch1, 5, "plant " + "grows towards the light " * 5)
    add(db, plants, ch2, 1, "plant " + "in another chapter " * 20)
    add(db, rivers, geo, 1, "plant " + "by the river bank " * 20)
    settings = Settings(rerank_enabled=True)

    plain = search(db, EMB, Scope.chapters([ch1.id]), "plant")
    reranked = search(
        db, EMB, Scope.chapters([ch1.id]), "plant", rerank=make_reranker(settings)
    )
    assert plain[0].id == short
    assert reranked[0].id == long
    assert {i for h in reranked for i in h.chunk_ids} == {short, long}

    in_material = search(
        db, EMB, Scope.materials([plants.id]), "plant", rerank=make_reranker(settings)
    )
    assert in_material
    assert {h.material_id for h in in_material} == {plants.id}


@pytest.mark.skipif(
    "EMBED_CACHE_DIR" not in os.environ,
    reason="downloads the real model; set EMBED_CACHE_DIR to run",
)
def test_real_cross_encoder_prefers_the_answer():
    settings = Settings()
    scorer = FastCrossEncoder(settings.rerank_model, settings.embed_cache_dir)
    right, wrong = scorer(
        "How do plants make their food?",
        [
            "Leaves make food from sunlight by photosynthesis.",
            "Rivers carry water to the sea.",
        ],
    )
    assert right > wrong
