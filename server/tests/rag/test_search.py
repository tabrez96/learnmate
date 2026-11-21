from dataclasses import replace

import numpy as np
import pytest

from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import LlmUnavailableError, SearchQuery, Turn, Usage
from learnmate.models import Chapter, Chunk, Figure, Material, Subject
from learnmate.rag.embed import encode
from learnmate.rag.search import (
    Candidate,
    Scope,
    below_floor,
    merge_neighbours,
    no_rerank,
    rrf,
    search,
    search_query,
)


class WordEmbedder:
    model = "word"

    def embed(self, texts):
        rows = []
        for text in texts:
            t = text.lower()
            rows.append(
                [1, 0, 0] if "plant" in t else [0, 1, 0] if "river" in t else [0, 0, 1]
            )
        return np.array(rows, dtype=np.float32)


EMB = WordEmbedder()


@pytest.fixture
def world(db):
    science = Subject(name="Science", icon="flask")
    geography = Subject(name="Geography", icon="globe")
    db.add_all([science, geography])
    db.flush()
    plants = Material(subject_id=science.id, title="Plants", kind="upload")
    rivers = Material(subject_id=geography.id, title="Rivers", kind="upload")
    db.add_all([plants, rivers])
    db.flush()
    ch1 = Chapter(material_id=plants.id, name="One", position=1)
    ch2 = Chapter(material_id=plants.id, name="Two", position=2)
    geo = Chapter(material_id=rivers.id, name="Rivers", position=1)
    db.add_all([ch1, ch2, geo])
    db.flush()
    return {"plants": plants, "rivers": rivers, "ch1": ch1, "ch2": ch2, "geo": geo}


def add(db, material, chapter, position, text, embed=True):
    row = Chunk(
        material_id=material.id,
        chapter_id=chapter.id if chapter else None,
        page=position,
        position=position,
        text=text,
        embedding=encode(EMB, [text])[0] if embed else None,
        embed_model="word" if embed else None,
    )
    db.add(row)
    db.flush()
    return row.id


def add_figure(db, material, chapter, position, description):
    figure = Figure(
        material_id=material.id,
        chapter_id=chapter.id,
        page=position,
        path=f"{material.id}/fig-{position}.png",
        description=description,
    )
    db.add(figure)
    db.flush()
    row = Chunk(
        material_id=material.id,
        chapter_id=chapter.id,
        page=position,
        position=position,
        kind="figure",
        figure_id=figure.id,
        text=description,
        embedding=encode(EMB, [description])[0],
        embed_model="word",
    )
    db.add(row)
    db.flush()
    return figure.id


def cand(id, position, score=0.5, text="text", chapter=1, material=1):
    return Candidate(id, material, chapter, 1, position, text, score)


def test_rrf_fixed_rankings():
    result = rrf([[1, 2, 3], [3, 1]])
    assert [i for i, _ in result] == [1, 3, 2]
    expected = [1 / 61 + 1 / 62, 1 / 63 + 1 / 61, 1 / 62]
    assert [s for _, s in result] == pytest.approx(expected)


def test_rrf_ties_break_by_id():
    assert rrf([[5], [4]]) == [(4, pytest.approx(1 / 61)), (5, pytest.approx(1 / 61))]
    assert rrf([]) == []


def test_merge_neighbours_joins_adjacent_hits():
    hits = merge_neighbours([cand(13, 3, 0.9), cand(17, 7, 0.8), cand(14, 4, 0.7)])
    assert len(hits) == 2
    assert hits[0].chunk_ids == [13, 14]
    assert hits[0].id == 13
    assert hits[0].score == 0.9
    assert hits[1].chunk_ids == [17]


def test_merge_neighbours_removes_overlap():
    a = "Start of the first part. Overlap text that repeats here."
    b = "Overlap text that repeats here. And the second part goes on."
    [hit] = merge_neighbours([cand(1, 1, text=a), cand(2, 2, text=b)])
    assert hit.text.count("Overlap text that repeats here.") == 1
    assert hit.text.startswith("Start of the first part.")
    assert hit.text.endswith("the second part goes on.")


def test_merge_neighbours_without_overlap_joins_with_newline():
    [hit] = merge_neighbours([cand(1, 1, text="aaa"), cand(2, 2, text="bbb")])
    assert hit.text == "aaa\nbbb"


def test_merge_neighbours_keeps_chapters_apart():
    hits = merge_neighbours([cand(1, 5, chapter=1), cand(2, 6, chapter=2)])
    assert len(hits) == 2


def test_merge_neighbours_bridges_two_runs():
    hits = merge_neighbours([cand(1, 1, 0.9), cand(3, 3, 0.8), cand(2, 2, 0.7)])
    assert len(hits) == 1
    assert hits[0].chunk_ids == [1, 2, 3]


def test_merge_neighbours_caps_passages_and_chars():
    small = [cand(i, i * 2, text="x" * 100) for i in range(8)]
    assert len(merge_neighbours(small)) == 6
    big = [cand(i, i * 2, text="x" * 1000) for i in range(10)]
    hits = merge_neighbours(big)
    assert len(hits) == 5
    assert sum(len(h.text) for h in hits) <= 5000
    assert len(merge_neighbours([cand(1, 1, text="x" * 6000)])) == 1


@pytest.mark.parametrize(
    ("best", "hits", "expected"),
    [
        (0.2, 0, True),
        (None, 0, True),
        (0.2, 1, False),
        (0.5, 0, False),
        (0.35, 0, False),
    ],
)
def test_below_floor(best, hits, expected):
    assert below_floor(best, hits, 0.35) is expected


def test_search_stays_in_chapter_scope(db, world):
    w = world
    one = add(db, w["plants"], w["ch1"], 1, "A plant makes food.")
    add(db, w["plants"], w["ch2"], 1, "Another plant grows.")
    add(db, w["rivers"], w["geo"], 1, "A plant by the river.")
    hits = search(db, EMB, Scope.chapters([w["ch1"].id]), "plant")
    assert [i for h in hits for i in h.chunk_ids] == [one]


def test_search_stays_in_material_scope(db, world):
    w = world
    river = add(db, w["rivers"], w["geo"], 1, "The river flows to the sea.")
    loose = add(db, w["rivers"], None, 2, "Another river fact.")
    plant = add(db, w["plants"], w["ch1"], 1, "A plant near a river.")
    hits = search(db, EMB, Scope.materials([w["rivers"].id]), "river")
    assert sorted(i for h in hits for i in h.chunk_ids) == [river, loose]
    science = search(db, EMB, Scope.materials([w["plants"].id]), "river")
    assert [i for h in science for i in h.chunk_ids] == [plant]
    assert search(db, EMB, Scope.chapters([w["geo"].id]), "river")[0].chunk_ids == [
        river
    ]


def test_search_off_topic_returns_empty(db, world):
    w = world
    add(db, w["plants"], w["ch1"], 1, "A plant makes food.")
    assert search(db, EMB, Scope.chapters([w["ch1"].id]), "football scores") == []


def test_search_returns_ids_scores_and_merges(db, world):
    w = world
    a = add(db, w["plants"], w["ch1"], 1, "A plant makes food.")
    b = add(db, w["plants"], w["ch1"], 2, "A plant drinks water.")
    add(db, w["plants"], w["ch2"], 1, "Plant roots.")
    hits = search(db, EMB, Scope.materials([w["plants"].id]), "plant")
    merged = next(h for h in hits if len(h.chunk_ids) == 2)
    assert merged.chunk_ids == [a, b]
    assert merged.score > 0
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_search_skips_other_model_vectors(db, world):
    w = world
    stale = Chunk(
        material_id=w["plants"].id,
        chapter_id=w["ch1"].id,
        page=1,
        position=9,
        text="A plant, stale vector.",
        embedding=np.ones(5, dtype=np.float32).tobytes(),
        embed_model="other",
    )
    db.add(stale)
    db.flush()
    hits = search(db, EMB, Scope.chapters([w["ch1"].id]), "plant")
    assert [i for h in hits for i in h.chunk_ids] == [stale.id]


def _flip(query, candidates):
    """Scores the last candidate highest, like a reranker that disagrees."""
    flipped = candidates[::-1]
    return [replace(c, score=float(n)) for n, c in enumerate(reversed(flipped), 1)][
        ::-1
    ]


def test_search_calls_rerank_hook(db, world):
    w = world
    a = add(db, w["plants"], w["ch1"], 1, "A plant makes food.")
    add(db, w["plants"], w["ch1"], 5, "Plants need light.")
    scope = Scope.chapters([w["ch1"].id])
    plain = search(db, EMB, scope, "plant")
    reversed_ = search(db, EMB, scope, "plant", rerank=_flip)
    assert [h.id for h in plain] != [h.id for h in reversed_]
    assert a in {h.id for h in plain}
    assert no_rerank("q", [cand(1, 1)]) == [cand(1, 1)]


def test_search_empty_query_or_scope(db, world):
    w = world
    add(db, w["plants"], w["ch1"], 1, "A plant makes food.")
    assert search(db, EMB, Scope.chapters([w["ch1"].id]), "  ") == []
    assert search(db, EMB, Scope.chapters([]), "plant") == []


def test_search_query_first_question_unchanged(settings):
    llm = FakeLlm(settings)
    assert search_query(llm, "What is rain?", []) == "What is rain?"
    assert llm.calls == []


class StubLlm:
    def __init__(self, error=None):
        self.error = error
        self.seen = None

    def rewrite_query(self, question, *, history):
        self.seen = (question, history)
        if self.error:
            raise self.error
        return type("R", (), {"value": SearchQuery(query="water cycle evaporation")})()


HISTORY = [Turn(role="student", text="Tell me about the water cycle")]


def test_search_query_rewrites_follow_up():
    llm = StubLlm()
    assert (
        search_query(llm, "why does it do that?", HISTORY) == "water cycle evaporation"
    )
    assert llm.seen == ("why does it do that?", HISTORY)


def test_search_query_falls_back_on_error():
    llm = StubLlm(LlmUnavailableError("x", Usage("m", "rewrite")))
    assert search_query(llm, "why?", HISTORY) == "why?"


def test_search_uses_given_floor(db, world):
    w = world
    add(db, w["plants"], w["ch1"], 1, "A plant makes food.")
    scope = Scope.chapters([w["ch1"].id])
    assert len(search(db, EMB, scope, "houseplant")) == 1
    assert search(db, EMB, scope, "houseplant", min_similarity=1.01) == []


def test_scoped_search_finds_figure_chunk(db, world):
    w = world
    figure_id = add_figure(
        db, w["plants"], w["ch1"], 1, "Diagram of a leaf cross section"
    )
    add_figure(db, w["rivers"], w["geo"], 1, "Diagram of a river leaf cross section")
    hits = search(db, EMB, Scope.chapters([w["ch1"].id]), "leaf cross section")
    assert [h.figure_id for h in hits] == [figure_id]
    assert search(db, EMB, Scope.chapters([w["ch2"].id]), "leaf cross section") == []


def test_figure_chunk_not_merged_with_neighbour_text(db, world):
    w = world
    add(db, w["plants"], w["ch1"], 0, "A plant leaf makes food.")
    figure_id = add_figure(db, w["plants"], w["ch1"], 1, "Diagram of a plant leaf")
    hits = search(db, EMB, Scope.chapters([w["ch1"].id]), "plant leaf")
    assert len(hits) == 2
    assert sorted(h.figure_id or 0 for h in hits) == [0, figure_id]
