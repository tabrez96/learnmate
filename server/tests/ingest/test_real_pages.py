from pathlib import Path

import pytest

from learnmate.config import Settings
from learnmate.files import ALLOWED
from learnmate.ingest.chapters import clean
from learnmate.ingest.pipeline import CHAPTER_PREVIEW_CHARS, page_text
from learnmate.ingest.readers import iter_pages
from learnmate.llm import make_llm

REAL_DIR = Path(__file__).resolve().parents[2] / "data" / "eval" / "real"


def test_real_pages_are_read(request):
    if not request.config.getoption("--real"):
        pytest.skip("pass --real to read the pages under data/eval/real/")
    paths = sorted(
        p for p in REAL_DIR.glob("*") if p.is_file() and p.suffix.lower() in ALLOWED
    )
    if not paths:
        pytest.skip(f"no pages under {REAL_DIR}")
    settings = Settings(llm_provider="anthropic")
    if not settings.anthropic_api_key:
        pytest.skip("ANTHROPIC_API_KEY is not set")
    llm = make_llm(settings)

    out = REAL_DIR / "out"
    out.mkdir(exist_ok=True)
    for path in paths:
        mime = ALLOWED[path.suffix.lower()][0]
        texts = [page_text(llm, raw) for raw in iter_pages(path, mime)]
        body = "".join(f"--- page {n} ---\n{t}\n" for n, t in enumerate(texts, 1))
        (out / f"{path.name}.txt").write_text(body)

        previews = [t[:CHAPTER_PREVIEW_CHARS] for t in texts]
        guesses = llm.detect_chapters(previews).value.chapters
        chapters = clean(guesses, len(texts), given=[], fallback=path.stem)
        lines = (f"page {c.start_page}: {c.name}" for c in chapters)
        (out / f"{path.name}.chapters.txt").write_text("\n".join(lines) + "\n")

        assert any(t.strip() for t in texts), f"{path.name} produced no text"
