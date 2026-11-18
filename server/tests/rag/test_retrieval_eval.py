"""The committed retrieval eval: invented chapters, the real embedding model."""

import os

import pytest

from learnmate.rag.embed import FastEmbedder
from learnmate.rag.search import Scope
from tests.rag.retrieval_eval import (
    RECALL_FLOOR,
    Outcome,
    answerable,
    build_corpus,
    floor_dependent,
    load_corpus,
    recall_at_k,
    report,
    run_question,
    snippet_matcher,
)

pytestmark = pytest.mark.skipif(
    "EMBED_CACHE_DIR" not in os.environ,
    reason="downloads the real model; set EMBED_CACHE_DIR to run",
)


@pytest.fixture
def evaluated(db, settings) -> list[Outcome]:
    corpus = load_corpus()
    embedder = FastEmbedder(settings.embed_model, settings.embed_cache_dir)
    chapter_ids = build_corpus(db, settings, embedder, corpus)
    return [
        run_question(
            db,
            embedder,
            Scope.chapters(chapter_ids[q["subject"]]),
            id=q["id"],
            kind=q["kind"],
            question=q["question"],
            relevant=snippet_matcher(q["expected"]),
            floor=settings.rag_min_similarity,
        )
        for q in corpus["questions"]
    ]


def test_recall_and_mrr(evaluated, settings, capsys):
    with capsys.disabled():
        print("\n" + report("committed set", evaluated, settings.rag_min_similarity))
    assert recall_at_k(evaluated) >= RECALL_FLOOR


def test_off_topic_questions_get_no_passages(evaluated, settings):
    off = [o for o in evaluated if o.kind == "off_topic"]
    assert off
    keyword_matched = [
        (o.id, o.keyword_hits, o.question) for o in off if o.keyword_hits
    ]
    assert not keyword_matched, (
        f"off-topic questions with keyword hits: {keyword_matched}"
    )
    dependent = floor_dependent(evaluated)
    assert len(dependent) >= 3, (
        f"only {len(dependent)} answerable questions have no keyword hit; the floor is untested"
    )
    highest_off = max(o.best_cosine for o in off)
    lowest_dependent = min(o.best_cosine for o in dependent)
    floor = settings.rag_min_similarity
    top_off = sorted(off, key=lambda o: o.best_cosine, reverse=True)[:3]
    low_dep = sorted(dependent, key=lambda o: o.best_cosine)[:3]
    # Checked before the per-question passages so the failure always carries the numbers.
    assert highest_off < floor <= lowest_dependent, (
        f"off-topic max cos={highest_off:.3f}, floor-dependent min cos={lowest_dependent:.3f}, "
        f"floor={floor:.2f}, suggested={round((highest_off + lowest_dependent) / 2, 2):.2f}; "
        f"top off-topic {[(o.id, round(o.best_cosine, 3)) for o in top_off]}; "
        f"lowest floor-dependent {[(o.id, round(o.best_cosine, 3)) for o in low_dep]}"
    )
    answered = [(o.id, o.passages, o.question) for o in off if o.passages]
    assert not answered, f"off-topic questions that got passages: {answered}"
    starved = [(o.id, o.question) for o in answerable(evaluated) if o.passages == 0]
    assert not starved, f"answerable questions that got no passages: {starved}"


def test_handwritten_questions_found_on_photos(evaluated):
    handwritten = [o for o in evaluated if o.kind == "handwritten"]
    assert recall_at_k(handwritten) >= RECALL_FLOOR
