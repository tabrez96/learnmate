import numpy as np
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from learnmate.clock import SystemClock
from learnmate.config import get_settings
from learnmate.db import create_db_engine, make_session_factory
from learnmate.main import create_app
from learnmate.models import Chapter, Chunk, Material, Subject
from learnmate.rag import reindex as reindex_module
from learnmate.rag.fake_embed import FakeEmbedder
from learnmate.rag.keyword import keyword_search
from learnmate.rag.reindex import reindex


def blob(model: str, dim: int = 4) -> bytes:
    return np.ones(dim, np.float32).tobytes()


def seed(db, specs, *, chapter=True):
    """specs: list of (text, embed_model); returns chunk ids."""
    subject = Subject(name="Science", icon="flask")
    db.add(subject)
    db.flush()
    material = Material(subject_id=subject.id, title="Unit", kind="upload")
    db.add(material)
    db.flush()
    row = Chapter(material_id=material.id, name="The Water Cycle", position=1)
    db.add(row)
    db.flush()
    ids = []
    for n, (body, model) in enumerate(specs, start=1):
        c = Chunk(
            material_id=material.id,
            chapter_id=row.id if chapter else None,
            page=1,
            position=n,
            text=body,
            embedding=blob(model) if model else None,
            embed_model=model,
        )
        db.add(c)
        db.flush()
        ids.append(c.id)
    db.commit()
    return ids


@pytest.fixture
def sessions(engine, clock):
    return make_session_factory(engine, clock)


def rows(sessions):
    with sessions() as db:
        return list(db.scalars(select(Chunk).order_by(Chunk.id)))


def test_reindex_all_switches_model_and_dimension(sessions):
    with sessions() as db:
        seed(db, [("one", "fake-a"), ("two", "fake-a"), ("three", "fake-a")])
    assert reindex(sessions, FakeEmbedder("fake-b", 6), only_stale=False) == 3
    for c in rows(sessions):
        vector = np.frombuffer(c.embedding, np.float32)
        assert c.embed_model == "fake-b"
        assert len(vector) == 6
        assert abs(np.linalg.norm(vector) - 1) < 1e-5


def test_reindex_all_rewrites_current_rows_too(sessions):
    with sessions() as db:
        seed(db, [("one", "fake-b"), ("two", "fake-b")])
    embedder = FakeEmbedder("fake-b", 4)
    assert reindex(sessions, embedder, only_stale=False) == 2
    assert reindex(sessions, embedder, only_stale=False) == 2


def test_reindex_empty_database(sessions):
    assert reindex(sessions, FakeEmbedder("fake-b"), only_stale=False) == 0


def test_reindex_stale_only_touches_stale_rows(sessions):
    with sessions() as db:
        seed(
            db,
            [("a", "fake-b"), ("b", "fake-b"), ("c", "fake-a"), ("d", None)],
        )
    before = {c.text: c.embedding for c in rows(sessions)}
    embedder = FakeEmbedder("fake-b", 4)
    assert reindex(sessions, embedder, only_stale=True) == 2
    texts = {t for batch in embedder.calls for t in batch}
    assert len(texts) == 2
    assert all(t.endswith(("\n\nc", "\n\nd")) for t in texts)
    after = {c.text: c for c in rows(sessions)}
    assert after["a"].embedding == before["a"]
    assert after["b"].embedding == before["b"]
    assert after["c"].embed_model == after["d"].embed_model == "fake-b"


def test_reindex_stale_includes_missing_embedding(sessions):
    with sessions() as db:
        (cid,) = seed(db, [("a", "fake-b")])
        db.get(Chunk, cid).embedding = None
        db.commit()
    assert reindex(sessions, FakeEmbedder("fake-b"), only_stale=True) == 1
    assert rows(sessions)[0].embedding is not None


def test_reindex_handles_chunk_without_chapter(sessions):
    with sessions() as db:
        seed(db, [("Rain falls.", "fake-a")], chapter=False)
    embedder = FakeEmbedder("fake-b")
    reindex(sessions, embedder, only_stale=False)
    assert embedder.calls == [["Science / Unit\n\nRain falls."]]


def test_reindex_batches_commit(sessions, monkeypatch):
    monkeypatch.setattr(reindex_module, "BATCH", 2)
    with sessions() as db:
        seed(db, [(f"t{n}", "fake-a") for n in range(5)])
    embedder = FakeEmbedder("fake-b")
    assert reindex(sessions, embedder, only_stale=False) == 5
    assert [len(b) for b in embedder.calls] == [2, 2, 1]
    assert {c.embed_model for c in rows(sessions)} == {"fake-b"}


def test_reindex_keeps_finished_batches_when_a_later_one_fails(sessions, monkeypatch):
    monkeypatch.setattr(reindex_module, "BATCH", 2)
    with sessions() as db:
        seed(db, [(f"t{n}", "fake-a") for n in range(4)])

    class FailsSecond(FakeEmbedder):
        def embed(self, texts):
            if self.calls:
                raise RuntimeError("boom")
            return super().embed(texts)

    with pytest.raises(RuntimeError):
        reindex(sessions, FailsSecond("fake-b"), only_stale=False)
    assert [c.embed_model for c in rows(sessions)] == [
        "fake-b",
        "fake-b",
        "fake-a",
        "fake-a",
    ]


def test_reindex_skips_chunk_deleted_while_encoding(sessions):
    with sessions() as db:
        first, second = seed(db, [("one", "fake-a"), ("two", "fake-a")])

    class DeletesFirst(FakeEmbedder):
        def embed(self, texts):
            with sessions() as db:
                db.delete(db.get(Chunk, first))
                db.commit()
            return super().embed(texts)

    assert reindex(sessions, DeletesFirst("fake-b"), only_stale=False) == 1
    (left,) = rows(sessions)
    assert left.id == second
    assert left.embed_model == "fake-b"


def test_reindex_does_not_overwrite_chunk_reusing_a_deleted_id(sessions):
    with sessions() as db:
        (cid,) = seed(db, [("old text", "fake-a")])
    replacement = np.ones(4, np.float32).tobytes()

    class ReplacesRow(FakeEmbedder):
        def embed(self, texts):
            with sessions() as db:
                old = db.get(Chunk, cid)
                material_id = old.material_id
                db.delete(old)
                db.commit()
                db.add(
                    Chunk(
                        id=cid,
                        material_id=material_id,
                        page=1,
                        position=1,
                        text="new text",
                        embedding=replacement,
                        embed_model="fake-a",
                    )
                )
                db.commit()
            return super().embed(texts)

    assert reindex(sessions, ReplacesRow("fake-b"), only_stale=False) == 0
    (row,) = rows(sessions)
    assert row.text == "new text"
    assert row.embed_model == "fake-a"
    assert row.embedding == replacement


def test_reindex_does_not_touch_fts(sessions):
    with sessions() as db:
        seed(db, [("Photosynthesis needs light.", "fake-a")])
        chapter_ids = list(db.scalars(select(Chapter.id)))
    reindex(sessions, FakeEmbedder("fake-b"), only_stale=False)
    with sessions() as db:
        db.execute(text("INSERT INTO chunk_fts(chunk_fts) VALUES('integrity-check')"))
        assert keyword_search(db, "photosynthesis", chapter_ids=chapter_ids, limit=5)


def test_main_uses_configured_model(alembic_config, tmp_path, monkeypatch, capsys):
    data = tmp_path / "main-data"
    data.mkdir()
    url = f"sqlite:///{data / 'learnmate.db'}"
    alembic_config.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(url)
    sessions = make_session_factory(engine, SystemClock())
    with sessions() as db:
        seed(db, [("one", "fake-a")])
    engine.dispose()
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("EMBED_PROVIDER", "fake")
    monkeypatch.setenv("EMBED_MODEL", "fake-z")
    get_settings.cache_clear()
    try:
        reindex_module.main()
    finally:
        get_settings.cache_clear()
    assert "Re-embedded 1 chunks with fake-z" in capsys.readouterr().out
    engine = create_db_engine(url)
    with make_session_factory(engine, SystemClock())() as db:
        assert db.scalars(select(Chunk.embed_model)).all() == ["fake-z"]
    engine.dispose()


def test_startup_reembeds_stale_rows_only(app, settings):
    settings.embed_model = "fake-new"
    application = create_app(settings)
    sessions = application.state.session_factory
    with sessions() as db:
        old, current = seed(db, [("old", "fake-old"), ("new", "fake-new")])
    before = {c.id: c.embedding for c in rows(sessions)}
    with TestClient(application):
        pass
    after = {c.id: c for c in rows(sessions)}
    assert after[old].embed_model == "fake-new"
    assert after[current].embedding == before[current]
    application.state.engine.dispose()


def test_startup_survives_embedder_failure(app, settings):
    class Broken(FakeEmbedder):
        def embed(self, texts):
            raise RuntimeError("model unavailable")

    application = create_app(settings)
    application.state.embedder = Broken("fake-new")
    sessions = application.state.session_factory
    with sessions() as db:
        (old,) = seed(db, [("old", "fake-old")])
    with TestClient(application) as client:
        assert client.get("/api/v1/health").status_code == 200
    assert rows(sessions)[0].embed_model == "fake-old"
    assert rows(sessions)[0].id == old
    application.state.engine.dispose()
