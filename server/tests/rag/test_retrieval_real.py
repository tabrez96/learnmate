"""The retrieval eval on real pages under data/eval/real/ (outside git); runs only with --real."""

from pathlib import Path

import pytest
import yaml

from learnmate.config import Settings
from learnmate.files import ALLOWED
from learnmate.ingest.chapters import clean
from learnmate.ingest.pipeline import CHAPTER_PREVIEW_CHARS, page_text
from learnmate.ingest.readers import iter_pages
from learnmate.llm import make_llm
from learnmate.models import Subject
from learnmate.rag.embed import FastEmbedder
from learnmate.rag.search import Scope
from tests.rag.retrieval_eval import (
    add_material,
    answerable,
    page_matcher,
    report,
    run_question,
)

REAL_DIR = Path(__file__).resolve().parents[2] / "data" / "eval" / "real"


def expected_pages(refs: list[str]) -> set[tuple[str, int]]:
    """'civics-ch3.pdf:2' is page 2 of the file civics-ch3.pdf."""
    pairs = (ref.rsplit(":", 1) for ref in refs)
    return {(name, int(page)) for name, page in pairs}


def test_real_retrieval_set(request, db, capsys):
    if not request.config.getoption("--real"):
        pytest.skip("pass --real to run the real retrieval set")
    questions_file = REAL_DIR / "questions.yaml"
    if not questions_file.is_file():
        pytest.skip(f"no {questions_file}")
    paths = sorted(
        p for p in REAL_DIR.glob("*") if p.is_file() and p.suffix.lower() in ALLOWED
    )
    if not paths:
        pytest.skip(f"no pages under {REAL_DIR}")
    settings = Settings(llm_provider="anthropic")
    if not settings.anthropic_api_key:
        pytest.skip("ANTHROPIC_API_KEY is not set")
    llm = make_llm(settings)
    embedder = FastEmbedder(settings.embed_model, settings.embed_cache_dir)

    subject = Subject(name="Real set", icon="book")
    db.add(subject)
    db.flush()
    chapter_ids: list[int] = []
    for path in paths:
        mime = ALLOWED[path.suffix.lower()][0]
        texts = [page_text(llm, raw) for raw in iter_pages(path, mime)]
        previews = [t[:CHAPTER_PREVIEW_CHARS] for t in texts]
        guesses = llm.detect_chapters(previews).value.chapters
        chapters = clean(guesses, len(texts), given=[], fallback=path.stem)
        chapter_ids += add_material(
            db,
            embedder,
            subject=subject,
            title=path.name,
            chapter_names=[c.name for c in chapters],
            starts=[c.start_page for c in chapters],
            texts=texts,
        )

    scope = Scope.chapters(chapter_ids)
    floor = settings.rag_min_similarity
    outcomes = []
    for q in yaml.safe_load(questions_file.read_text()):
        off_topic = bool(q.get("off_topic"))
        outcomes.append(
            run_question(
                db,
                embedder,
                scope,
                id=q["id"],
                kind="off_topic" if off_topic else "real",
                question=q["question"],
                relevant=page_matcher(db, expected_pages(q.get("expected", []))),
                floor=floor,
            )
        )
    with capsys.disabled():
        print("\n" + report("real set", outcomes, floor))
    assert answerable(outcomes), "questions.yaml has no answerable questions"
