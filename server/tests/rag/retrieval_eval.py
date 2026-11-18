"""Shared harness for the retrieval evaluation: load a material, ask questions, score."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.config import Settings
from learnmate.ingest.pipeline import embedded_chunks, page_text
from learnmate.ingest.readers import iter_pages
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import LlmResult, PageText
from learnmate.models import Chapter, Chunk, Material, Subject
from learnmate.rag.embed import Embedder
from learnmate.rag.keyword import keyword_search
from learnmate.rag.search import Scope, SearchHit, search, vector_search

K = 6
RECALL_FLOOR = 0.85
EVAL = Path(__file__).resolve().parent / "eval"


@dataclass(frozen=True)
class Outcome:
    id: str
    kind: (
        str  # paraphrase | exact | handwritten | off_topic (real set: real | off_topic)
    )
    question: str
    rank: int | None  # 1-based rank of the first relevant passage; None if missed
    passages: int  # passages search returned
    best_cosine: float | None
    keyword_hits: int


def add_material(
    db: Session,
    embedder: Embedder,
    *,
    subject: Subject,
    title: str,
    chapter_names: list[str],
    starts: list[int],
    texts: list[str],
) -> list[int]:
    """Insert a ready material with its chapters and embedded chunks, like ingestion does; returns chapter ids."""
    material = Material(
        subject_id=subject.id, title=title, kind="upload", status="ready"
    )
    db.add(material)
    db.flush()
    chapters = [
        Chapter(material_id=material.id, name=name, position=i)
        for i, name in enumerate(chapter_names, start=1)
    ]
    db.add_all(chapters)
    db.flush()
    _, embedded = embedded_chunks(
        embedder, subject.name, title, chapter_names, starts, texts
    )
    db.add_all(
        Chunk(
            material_id=material.id,
            chapter_id=chapters[draft.chapter].id,
            page=draft.page,
            position=draft.position,
            text=draft.text,
            embedding=blob,
            embed_model=embedder.model,
        )
        for draft, blob in embedded
    )
    db.flush()
    return [c.id for c in chapters]


class RecordedLlm(FakeLlm):
    """Vision output recorded in the corpus instead of a live model call."""

    def __init__(self, settings: Settings, text: str) -> None:
        super().__init__(settings)
        self.text = text

    def read_page(self, image: bytes, media_type: str) -> LlmResult[PageText]:
        usage = super().read_page(image, media_type).usage
        return LlmResult(PageText(text=self.text), usage)


def load_corpus() -> dict:
    """corpus.yaml as a dict."""
    return yaml.safe_load((EVAL / "corpus.yaml").read_text())


def build_corpus(
    db: Session, settings: Settings, embedder: Embedder, corpus: dict
) -> dict[str, list[int]]:
    """Insert every subject and material of the corpus; returns subject name -> chapter ids."""
    chapter_ids: dict[str, list[int]] = {}
    for spec in corpus["subjects"]:
        subject = Subject(name=spec["name"], icon=spec["icon"])
        db.add(subject)
        db.flush()
        chapter_ids[spec["name"]] = []
        for material in spec["materials"]:
            texts: list[str] = []
            starts: list[int] = []
            for chapter in material["chapters"]:
                starts.append(len(texts) + 1)
                for page in chapter["pages"]:
                    if "photo" in page:
                        llm = RecordedLlm(settings, page["vision_text"])
                        (raw,) = iter_pages(
                            EVAL / "photos" / page["photo"], "image/jpeg"
                        )
                        texts.append(page_text(llm, raw))
                    else:
                        texts.append(page["text"])
            chapter_ids[spec["name"]] += add_material(
                db,
                embedder,
                subject=subject,
                title=material["title"],
                chapter_names=[c["name"] for c in material["chapters"]],
                starts=starts,
                texts=texts,
            )
    return chapter_ids


def normalise(text: str) -> str:
    return " ".join(text.lower().split())


def snippet_matcher(snippets: list[str]) -> Callable[[SearchHit], bool]:
    wanted = [normalise(s) for s in snippets]
    return lambda hit: any(s in normalise(hit.text) for s in wanted)


def page_matcher(
    db: Session, expected: set[tuple[str, int]]
) -> Callable[[SearchHit], bool]:
    """A hit is relevant when one of its chunks starts on an expected (material title, page)."""

    def matches(hit: SearchHit) -> bool:
        rows = db.execute(
            select(Material.title, Chunk.page)
            .join(Chunk, Chunk.material_id == Material.id)
            .where(Chunk.id.in_(hit.chunk_ids))
        )
        return any((title, page) in expected for title, page in rows)

    return matches


def run_question(
    db: Session,
    embedder: Embedder,
    scope: Scope,
    *,
    id: str,
    kind: str,
    question: str,
    relevant: Callable[[SearchHit], bool],
    floor: float,
) -> Outcome:
    hits = search(db, embedder, scope, question, min_similarity=floor)
    rank = next((i for i, h in enumerate(hits[:K], start=1) if relevant(h)), None)
    best = vector_search(db, embedder, scope, question)[1]
    keyword = keyword_search(db, question, chapter_ids=list(scope.ids))
    return Outcome(id, kind, question, rank, len(hits), best, len(keyword))


def answerable(outcomes: list[Outcome]) -> list[Outcome]:
    return [o for o in outcomes if o.kind != "off_topic"]


def floor_dependent(outcomes: list[Outcome]) -> list[Outcome]:
    """Answerable questions with no keyword hit: the only ones the relevance floor can drop."""
    return [o for o in answerable(outcomes) if o.keyword_hits == 0]


def recall_at_k(outcomes: list[Outcome]) -> float:
    rows = answerable(outcomes)
    return sum(o.rank is not None for o in rows) / len(rows) if rows else 0.0


def mrr(outcomes: list[Outcome]) -> float:
    rows = answerable(outcomes)
    return sum(1 / o.rank if o.rank else 0 for o in rows) / len(rows) if rows else 0.0


def report(title: str, outcomes: list[Outcome], floor: float) -> str:
    lines = [f"== {title} =="]
    for o in outcomes:
        if o.kind == "off_topic":
            verdict = "REJECTED" if o.passages == 0 else "ANSWERED"
        else:
            verdict = f"HIT@{o.rank}" if o.rank else "MISS"
        lines.append(
            f"{o.id:<6} {o.kind:<11} {verdict:<8} cos={o.best_cosine or 0:.3f} "
            f"kw={o.keyword_hits:<2} {o.question}"
        )
    off = [o for o in outcomes if o.kind == "off_topic"]
    rejected = sum(o.passages == 0 for o in off)
    off_max = max((o.best_cosine or 0 for o in off), default=0)
    dependent = floor_dependent(outcomes)
    dep_min = (
        f"{min(o.best_cosine or 0 for o in dependent):.3f}" if dependent else "n/a"
    )
    lines.append(
        f"recall@{K}={recall_at_k(outcomes):.3f}  MRR={mrr(outcomes):.3f}  "
        f"off-topic rejected {rejected}/{len(off)}  max off-topic cos={off_max:.3f}  "
        f"min floor-dependent cos={dep_min}  floor={floor:.2f}"
    )
    return "\n".join(lines)
