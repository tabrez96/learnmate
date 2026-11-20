"""The committed retrieval eval: invented chapters, the real embedding model."""

import datetime as dt
import os

import pytest
from alembic import command
from alembic.config import Config

from learnmate.clock import FakeClock
from learnmate.config import Settings
from learnmate.db import create_db_engine, make_session_factory
from learnmate.rag.embed import FastEmbedder
from learnmate.rag.rerank import RERANK_MAX_SECONDS, make_reranker
from learnmate.rag.search import Scope
from tests.conftest import SERVER_DIR
from tests.rag.retrieval_eval import (
    RECALL_FLOOR,
    Outcome,
    answerable,
    build_corpus,
    floor_dependent,
    load_corpus,
    mean_seconds,
    mrr,
    recall_at_k,
    report,
    run_question,
    snippet_matcher,
    warm_up,
)

pytestmark = pytest.mark.skipif(
    "EMBED_CACHE_DIR" not in os.environ,
    reason="downloads the real model; set EMBED_CACHE_DIR to run",
)


@pytest.fixture(scope="module")
def eval_settings(tmp_path_factory) -> Settings:
    return Settings(
        data_dir=tmp_path_factory.mktemp("data"),
        llm_provider="fake",
        embed_provider="fake",
    )


@pytest.fixture(scope="module")
def evaluation(tmp_path_factory, eval_settings) -> dict[bool, list[Outcome]]:
    """Every question searched with the reranker off and on, keyed by "rerank on"."""
    url = f"sqlite:///{tmp_path_factory.mktemp('db') / 'eval.db'}"
    cfg = Config(str(SERVER_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_db_engine(url)
    try:
        clock = FakeClock(dt.datetime(2026, 1, 5, 9, 0))
        with make_session_factory(engine, clock)() as db:
            corpus = load_corpus()
            embedder = FastEmbedder(
                eval_settings.embed_model, eval_settings.embed_cache_dir
            )
            chapter_ids = build_corpus(db, eval_settings, embedder, corpus)
            results = {}
            for on in (False, True):
                rerank = make_reranker(
                    eval_settings.model_copy(update={"rerank_enabled": on})
                )
                warm_up(embedder, rerank)
                results[on] = [
                    run_question(
                        db,
                        embedder,
                        Scope.chapters(chapter_ids[q["subject"]]),
                        id=q["id"],
                        kind=q["kind"],
                        question=q["question"],
                        relevant=snippet_matcher(q["expected"]),
                        floor=eval_settings.rag_min_similarity,
                        rerank=rerank,
                    )
                    for q in corpus["questions"]
                ]
            return results
    finally:
        engine.dispose()


@pytest.fixture
def evaluated(evaluation, eval_settings) -> list[Outcome]:
    """The default configuration."""
    return evaluation[eval_settings.rerank_enabled]


def test_recall_and_mrr(evaluation, eval_settings, capsys):
    floor = eval_settings.rag_min_similarity
    with capsys.disabled():
        print("\n" + report("committed set, rerank off", evaluation[False], floor))
        print("\n" + report("committed set, rerank on", evaluation[True], floor))
    assert recall_at_k(evaluation[eval_settings.rerank_enabled]) >= RECALL_FLOOR


def test_rerank_default_matches_eval(evaluation, eval_settings):
    off, on = evaluation[False], evaluation[True]
    numbers = (
        f"recall@6 off={recall_at_k(off):.3f} on={recall_at_k(on):.3f}, "
        f"MRR off={mrr(off):.3f} on={mrr(on):.3f}, "
        f"s/question off={mean_seconds(off):.3f} on={mean_seconds(on):.3f}"
    )
    if eval_settings.rerank_enabled:
        assert (
            recall_at_k(on) > recall_at_k(off)
            and mean_seconds(on) <= RERANK_MAX_SECONDS
        ), (
            f"rerank is on by default but does not improve recall@6 within {RERANK_MAX_SECONDS} s: {numbers}"
        )
    else:
        helps = recall_at_k(on) > recall_at_k(off)
        assert not helps or mean_seconds(on) > RERANK_MAX_SECONDS, (
            f"rerank improves recall@6 within {RERANK_MAX_SECONDS} s but is off by default: {numbers}"
        )


def test_off_topic_questions_get_no_passages(evaluated, eval_settings):
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
    floor = eval_settings.rag_min_similarity
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
