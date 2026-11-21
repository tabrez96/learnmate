import shutil
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw
from sqlalchemy import func, select, text

from learnmate.db import make_session_factory
from learnmate.ingest import ingest
from learnmate.ingest.pipeline import (
    AI_DOWN_MESSAGE,
    DAMAGED_MESSAGE,
    NO_TEXT_MESSAGE,
    UNEXPECTED_MESSAGE,
)
from learnmate.llm.budget import REACHED_MESSAGE
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import (
    ChapterGuess,
    ChapterList,
    FigureBox,
    FigureList,
    LlmResult,
    LlmUnavailableError,
    PageText,
    Usage,
)
from learnmate.models import (
    Chapter,
    Chunk,
    Figure,
    Material,
    MaterialFile,
    MaterialPage,
    Subject,
)
from learnmate.rag.embed import embed_input
from learnmate.rag.fake_embed import FakeEmbedder
from learnmate.rag.keyword import keyword_search

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_TEXT = "Plants make food from sunlight."
MIMES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}
DAMAGED_PDF = b"%PDF-1.4\n" + b"\x00junk" * 50


class ScriptedLlm(FakeLlm):
    def __init__(
        self,
        settings,
        *,
        chapters: list[tuple[str, int]] | None = None,
        page_text: str | None = None,
        fail_read: bool = False,
        fail_chapters: bool = False,
        figures: list[FigureBox] | None = None,
        fail_figures: bool = False,
        on_read: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(settings)
        self.chapters = chapters
        self.page_text = page_text
        self.fail_read = fail_read
        self.fail_chapters = fail_chapters
        self.figures = figures or []
        self.fail_figures = fail_figures
        self.on_read = on_read

    def read_page(self, image, media_type):
        if self.on_read:
            self.on_read()
        if self.fail_read:
            raise LlmUnavailableError("down", Usage("m", "read_page"))
        result = super().read_page(image, media_type)
        if self.page_text is None:
            return result
        return LlmResult(PageText(text=self.page_text), result.usage)

    def find_figures(self, image, media_type):
        result = super().find_figures(image, media_type)
        if self.fail_figures:
            raise LlmUnavailableError("down", Usage("m", "figures"))
        return LlmResult(FigureList(figures=self.figures), result.usage)

    def detect_chapters(self, pages, *, hint=None):
        if self.fail_chapters:
            raise RuntimeError("boom")
        result = super().detect_chapters(pages, hint=hint)
        if self.chapters is None:
            return result
        guesses = [ChapterGuess(name=n, start_page=p) for n, p in self.chapters]
        return LlmResult(ChapterList(chapters=guesses), result.usage)


@pytest.fixture
def sessions(engine, clock):
    return make_session_factory(engine, clock)


@pytest.fixture
def make_material(sessions, settings):
    def make(files: list[str | tuple[str, bytes]], *, hint=None, status="reading"):
        with sessions() as db:
            subject = Subject(name="Science", icon="flask")
            db.add(subject)
            db.flush()
            material = Material(
                subject_id=subject.id,
                title="Unit",
                kind="upload",
                status=status,
                chapters_hint=hint,
            )
            db.add(material)
            db.flush()
            folder = settings.data_dir / "files" / str(material.id)
            folder.mkdir(parents=True)
            for n, item in enumerate(files, start=1):
                if isinstance(item, tuple):
                    suffix, data = item
                    (folder / f"{n:02d}{suffix}").write_bytes(data)
                else:
                    suffix = Path(item).suffix
                    shutil.copy(FIXTURES / item, folder / f"{n:02d}{suffix}")
                db.add(
                    MaterialFile(
                        material_id=material.id,
                        path=f"{material.id}/{n:02d}{suffix}",
                        mime=MIMES[suffix],
                        size=1,
                    )
                )
            db.commit()
            return material.id

    return make


@pytest.fixture
def run(sessions, settings, clock):
    def go(material_id, llm, *, cfg=None, embedder=None):
        ingest(
            sessions,
            cfg or settings,
            material_id,
            llm=llm,
            embedder=embedder or FakeEmbedder("fake-test"),
            clock=clock,
        )
        with sessions() as db:
            material = db.get(Material, material_id)
            pages = list(
                db.scalars(
                    select(MaterialPage)
                    .where(MaterialPage.material_id == material_id)
                    .order_by(MaterialPage.page)
                )
            )
            chapters = list(
                db.scalars(
                    select(Chapter)
                    .where(Chapter.material_id == material_id)
                    .order_by(Chapter.position)
                )
            )
            db.expunge_all()
            return material, pages, chapters

    return go


def test_typed_pdf_ends_ready_with_pages_and_chapters(make_material, run, settings):
    llm = ScriptedLlm(
        settings, chapters=[("The Water Cycle", 1), ("Rocks and Soil", 3)]
    )
    material, pages, chapters = run(make_material(["typed.pdf"]), llm)
    assert material.status == "ready"
    assert material.error is None
    assert material.pages_total == material.pages_read == 3
    assert len(pages) == 3 and all(p.text for p in pages)
    assert [(c.name, c.position) for c in chapters] == [
        ("The Water Cycle", 1),
        ("Rocks and Soil", 2),
    ]
    assert [p.chapter_id for p in pages] == [
        chapters[0].id,
        chapters[0].id,
        chapters[1].id,
    ]
    assert "read_page" not in llm.calls


def test_word_file_produces_page_text(make_material, run, settings):
    material, pages, _ = run(make_material(["notes.docx"]), ScriptedLlm(settings))
    assert material.status == "ready"
    assert "A magnet pulls iron towards it." in pages[0].text


def test_scanned_pdf_is_read_by_vision(make_material, run, settings):
    llm = ScriptedLlm(settings)
    material, pages, _ = run(make_material(["scanned.pdf"]), llm)
    assert material.status == "ready"
    assert llm.calls.count("read_page") == 2
    assert [p.text for p in pages] == [FAKE_TEXT, FAKE_TEXT]


def test_phone_photo_is_read_by_vision(make_material, run, settings):
    material, pages, _ = run(
        make_material(["notebook_photo.jpg"]), ScriptedLlm(settings)
    )
    assert material.status == "ready"
    assert [p.text for p in pages] == [FAKE_TEXT]


def test_pages_numbered_across_files(make_material, run, settings):
    material, pages, _ = run(
        make_material(["typed.pdf", "notes.docx"]), ScriptedLlm(settings)
    )
    assert material.pages_total == 4
    assert [p.page for p in pages] == [1, 2, 3, 4]


def test_pages_read_increases_during_ingest(make_material, run, sessions, settings):
    mid = make_material(["scanned.pdf"])
    seen = []

    def observe():
        with sessions() as db:
            seen.append(db.get(Material, mid).pages_read)

    material, _, _ = run(mid, ScriptedLlm(settings, on_read=observe))
    assert seen == [0, 1]
    assert material.pages_read == 2


def test_given_chapter_names_are_respected(make_material, run, settings):
    llm = ScriptedLlm(
        settings, chapters=[("The Water Cycle", 1), ("Rocks and Soil", 3)]
    )
    _, _, chapters = run(make_material(["typed.pdf"], hint="Water; Rocks"), llm)
    assert [c.name for c in chapters] == ["Water", "Rocks"]


def test_damaged_file_ends_failed(make_material, run, settings):
    mid = make_material(["typed.pdf", (".pdf", DAMAGED_PDF)])
    llm = ScriptedLlm(settings)
    material, pages, chapters = run(mid, llm)
    assert material.status == "failed"
    assert material.error == DAMAGED_MESSAGE.format(n=2, total=2)
    assert pages == [] and chapters == []


def test_damaged_file_found_while_reading_ends_failed(
    make_material, run, settings, monkeypatch
):
    from learnmate.ingest import pipeline
    from learnmate.ingest.readers import UnreadableFile

    def broken(path, mime):
        raise UnreadableFile("bad")
        yield

    monkeypatch.setattr(pipeline, "iter_pages", broken)
    material, _, _ = run(make_material(["typed.pdf"]), ScriptedLlm(settings))
    assert material.error == DAMAGED_MESSAGE.format(n=1, total=1)


def test_budget_reached_ends_failed(make_material, run, settings):
    llm = ScriptedLlm(settings)
    cfg = settings.model_copy(update={"llm_monthly_budget_usd": 0})
    material, _, _ = run(make_material(["scanned.pdf"]), llm, cfg=cfg)
    assert material.status == "failed"
    assert material.error == REACHED_MESSAGE
    assert llm.calls == []


def test_ai_unavailable_ends_failed(make_material, run, settings):
    material, pages, _ = run(
        make_material(["scanned.pdf"]), ScriptedLlm(settings, fail_read=True)
    )
    assert material.status == "failed"
    assert material.error == AI_DOWN_MESSAGE.format(page=1)
    assert pages == []


def test_no_text_ends_failed(make_material, run, settings):
    material, _, _ = run(
        make_material(["scanned.pdf"]), ScriptedLlm(settings, page_text="  ")
    )
    assert material.status == "failed"
    assert material.error == NO_TEXT_MESSAGE


def test_unexpected_error_ends_failed(make_material, run, settings):
    material, pages, _ = run(
        make_material(["typed.pdf"]), ScriptedLlm(settings, fail_chapters=True)
    )
    assert material.status == "failed"
    assert material.error == UNEXPECTED_MESSAGE
    assert pages == []


def test_skips_material_not_reading(make_material, run, settings):
    llm = ScriptedLlm(settings)
    material, pages, _ = run(make_material(["typed.pdf"], status="ready"), llm)
    assert material.status == "ready"
    assert pages == [] and llm.calls == []


def test_stale_job_leaves_reused_id_alone(
    make_material, run, sessions, settings, clock
):
    old_id = make_material(["scanned.pdf"])
    seen = {}

    def replace_material():
        if seen:
            return
        with sessions() as db:
            db.delete(db.get(Material, old_id))
            db.commit()
            clock.advance(seconds=60)
            subject = db.scalars(select(Subject)).first()
            fresh = Material(
                subject_id=subject.id, title="New", kind="upload", status="reading"
            )
            db.add(fresh)
            db.flush()
            seen["id"] = fresh.id
            db.add(MaterialPage(material_id=fresh.id, page=1, text="keep me"))
            db.commit()

    material, pages, chapters = run(
        old_id, ScriptedLlm(settings, on_read=replace_material)
    )
    assert seen["id"] == old_id
    assert material.title == "New" and material.status == "reading"
    assert material.pages_read == 0
    assert [p.text for p in pages] == ["keep me"]
    assert chapters == []


def test_missing_material_is_ignored(run, settings):
    ingest_result = run(999, ScriptedLlm(settings))
    assert ingest_result[0] is None


def test_upload_runs_ingest_end_to_end(client, settings):
    subject = client.post("/api/v1/subjects", json={"name": "Science", "icon": "flask"})
    sid = subject.json()["id"]
    data = (FIXTURES / "typed.pdf").read_bytes()
    r = client.post(
        f"/api/v1/subjects/{sid}/materials",
        files=[("files", ("typed.pdf", data, "application/pdf"))],
    )
    body = client.get(f"/api/v1/materials/{r.json()['id']}").json()
    assert body["status"] == "ready"
    assert body["pages_read"] == 3
    assert len(body["chapters"]) >= 1
    with client.app.state.session_factory() as db:
        chunks = list(db.scalars(select(Chunk)))
    assert chunks
    assert all(c.embedding is not None for c in chunks)


CYCLE_CHAPTERS = [("The Water Cycle", 1), ("Rocks and Soil", 3)]


def _ingest_typed(make_material, run, settings):
    material, _, chapters = run(
        make_material(["typed.pdf"]), ScriptedLlm(settings, chapters=CYCLE_CHAPTERS)
    )
    return material, chapters


def test_ingest_stores_chunks_with_chapter_page_and_position(
    make_material, run, sessions, settings
):
    material, chapters = _ingest_typed(make_material, run, settings)
    with sessions() as db:
        chunks = list(
            db.scalars(
                select(Chunk)
                .where(Chunk.material_id == material.id)
                .order_by(Chunk.position)
            )
        )
    assert chunks
    assert [c.position for c in chunks] == list(range(1, len(chunks) + 1))
    assert {c.chapter_id for c in chunks} <= {c.id for c in chapters}
    assert all(1 <= c.page <= 3 for c in chunks)
    assert not any("vapour" in c.text and "Soil is a mix" in c.text for c in chunks)


def test_bm25_query_finds_known_term(make_material, run, sessions, settings):
    _, chapters = _ingest_typed(make_material, run, settings)
    ids = [c.id for c in chapters]
    with sessions() as db:
        vapour = keyword_search(db, "vapour", chapter_ids=ids)
        soil = keyword_search(db, "soil", chapter_ids=ids)
        first_vapour = db.get(Chunk, vapour[0][0])
        first_soil = db.get(Chunk, soil[0][0])
        assert "vapour" in first_vapour.text
        assert (first_vapour.page, first_vapour.chapter_id) == (1, chapters[0].id)
        assert (first_soil.page, first_soil.chapter_id) == (3, chapters[1].id)


def test_failed_ingest_leaves_no_chunks(make_material, run, sessions, settings):
    material, _, _ = run(
        make_material(["typed.pdf"]), ScriptedLlm(settings, fail_chapters=True)
    )
    with sessions() as db:
        assert (
            db.scalar(
                select(func.count(Chunk.id)).where(Chunk.material_id == material.id)
            )
            == 0
        )
        hits = db.scalar(
            text("SELECT count(*) FROM chunk_fts WHERE chunk_fts MATCH '\"water\"'")
        )
    assert hits == 0


class BrokenEmbedder:
    model = "broken"

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        raise RuntimeError("boom")


def _chunks(sessions, material_id):
    with sessions() as db:
        return list(
            db.scalars(
                select(Chunk)
                .where(Chunk.material_id == material_id)
                .order_by(Chunk.position)
            )
        )


def test_every_chunk_has_normalised_embedding(make_material, run, sessions, settings):
    material_id = make_material(["typed.pdf"])
    material, _, _ = run(
        material_id,
        ScriptedLlm(settings, chapters=CYCLE_CHAPTERS),
        embedder=FakeEmbedder("fake-a", dim=6),
    )
    chunks = _chunks(sessions, material.id)
    assert chunks
    for c in chunks:
        assert c.embed_model == "fake-a"
        vector = np.frombuffer(c.embedding, np.float32)
        assert len(vector) == 6
        assert abs(np.linalg.norm(vector) - 1) < 1e-5


def test_embedding_input_has_subject_title_chapter_prefix(
    make_material, run, sessions, settings
):
    embedder = FakeEmbedder("fake-a")
    material, _, _ = run(
        make_material(["typed.pdf"]),
        ScriptedLlm(settings, chapters=CYCLE_CHAPTERS),
        embedder=embedder,
    )
    chunks = _chunks(sessions, material.id)
    inputs = [t for batch in embedder.calls for t in batch]
    assert len(inputs) == len(chunks)
    with sessions() as db:
        names = {c.id: c.name for c in db.scalars(select(Chapter))}
    for sent, chunk in zip(inputs, chunks, strict=True):
        assert sent == embed_input(
            "Science", "Unit", names[chunk.chapter_id], chunk.text
        )
    assert {names[c.chapter_id] for c in chunks} == {
        "The Water Cycle",
        "Rocks and Soil",
    }


def test_embedder_failure_ends_failed(make_material, run, sessions, settings):
    embedder = BrokenEmbedder()
    material, _, _ = run(
        make_material(["typed.pdf"]),
        ScriptedLlm(settings, chapters=CYCLE_CHAPTERS),
        embedder=embedder,
    )
    assert embedder.calls == 1
    assert material.status == "failed"
    assert material.error == UNEXPECTED_MESSAGE
    assert _chunks(sessions, material.id) == []


DRAWING = "A leaf cross section with labels."


def _drawing_page() -> bytes:
    img = Image.new("RGB", (800, 1000), "white")
    ImageDraw.Draw(img).rectangle((200, 200, 600, 500), fill="black")
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _drawing_llm(settings, **kw) -> ScriptedLlm:
    box = FigureBox(description=DRAWING, box=[0.25, 0.2, 0.75, 0.5])
    return ScriptedLlm(settings, figures=[box], **kw)


def test_photo_with_drawing_yields_figure_crop_and_chunk(
    make_material, run, sessions, settings
):
    llm = _drawing_llm(settings)
    material, _, chapters = run(make_material([(".png", _drawing_page())]), llm)
    assert material.status == "ready"
    assert llm.calls == ["read_page", "figures", "chapters"]
    with sessions() as db:
        figure = db.scalars(select(Figure)).one()
        chunks = list(db.scalars(select(Chunk).order_by(Chunk.position)))
    assert (figure.description, figure.page) == (DRAWING, 1)
    assert figure.chapter_id == chapters[0].id
    assert figure.path.startswith(f"{material.id}/fig-")
    png = settings.data_dir / "files" / figure.path
    with Image.open(png) as crop:
        assert crop.format == "PNG"
        assert abs(crop.width - 400) <= 4 and abs(crop.height - 300) <= 4
    fig_chunk = chunks[-1]
    assert (fig_chunk.kind, fig_chunk.figure_id) == ("figure", figure.id)
    assert fig_chunk.text == DRAWING and fig_chunk.embedding is not None
    assert all(c.position < fig_chunk.position for c in chunks[:-1])
    assert len(chunks) > 1


def test_typed_pdf_does_not_ask_for_figures(make_material, run, settings):
    llm = _drawing_llm(settings)
    run(make_material(["typed.pdf"]), llm)
    assert "figures" not in llm.calls


def test_figure_llm_error_still_ready(make_material, run, sessions, settings):
    llm = _drawing_llm(settings, fail_figures=True)
    material, _, _ = run(make_material([(".png", _drawing_page())]), llm)
    assert material.status == "ready"
    with sessions() as db:
        assert db.scalar(select(func.count(Figure.id))) == 0


def test_failed_ingest_removes_figures(make_material, run, sessions, settings):
    llm = _drawing_llm(settings, fail_chapters=True)
    mid = make_material([(".png", _drawing_page())])
    material, _, _ = run(mid, llm)
    assert material.status == "failed"
    folder = settings.data_dir / "files" / str(mid)
    assert list(folder.glob("fig-*.png")) == []
    assert (folder / "01.png").exists()
    with sessions() as db:
        assert db.scalar(select(func.count(Figure.id))) == 0
        assert db.scalar(select(func.count(Chunk.id))) == 0


def test_figure_call_is_budget_checked(make_material, run, settings, monkeypatch):
    from learnmate.ingest import pipeline

    calls = []

    def check(*args):
        calls.append(1)
        if len(calls) == 3:  # start, before read_page, before figures
            raise pipeline.IngestFailed(REACHED_MESSAGE)

    monkeypatch.setattr(pipeline, "_check_budget", check)
    llm = _drawing_llm(settings)
    material, _, _ = run(make_material([(".png", _drawing_page())]), llm)
    assert material.status == "failed"
    assert llm.calls == ["read_page"]
