import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from learnmate.config import Settings
from learnmate.models import Base, Chunk, Material, Subject


def _include_object(obj, name, type_, reflected, compare_to) -> bool:
    return not (type_ == "table" and name.startswith("chunk_fts"))


@pytest.fixture
def chunk(db: Session) -> Chunk:
    subject = Subject(name="Science", icon="flask")
    db.add(subject)
    db.flush()
    material = Material(subject_id=subject.id, title="Notes", kind="upload")
    db.add(material)
    db.flush()
    row = Chunk(
        material_id=material.id, position=0, text="Photosynthesis makes glucose"
    )
    db.add(row)
    db.commit()
    return row


def _match(db: Session, word: str) -> list[int]:
    rows = db.execute(
        text("SELECT rowid FROM chunk_fts WHERE chunk_fts MATCH :w"), {"w": word}
    )
    return [r[0] for r in rows]


def test_upgrade_creates_all_tables(engine: Engine) -> None:
    expected = set(Base.metadata.tables) | {"chunk_fts"}
    assert expected <= set(inspect(engine).get_table_names())


def test_every_connection_uses_wal_and_foreign_keys(engine: Engine) -> None:
    with engine.connect() as a, engine.connect() as b:
        for conn in (a, b):
            assert conn.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_models_match_migration(engine: Engine) -> None:
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"include_object": _include_object})
        assert compare_metadata(ctx, Base.metadata) == []


def test_fts_follows_insert(db: Session, chunk: Chunk) -> None:
    assert _match(db, "photosynthesis") == [chunk.id]


def test_fts_follows_update(db: Session, chunk: Chunk) -> None:
    chunk.text = "Mitochondria release energy"
    db.commit()
    assert _match(db, "photosynthesis") == []
    assert _match(db, "mitochondria") == [chunk.id]


def test_fts_ignores_embedding_update(db: Session, chunk: Chunk) -> None:
    chunk.embedding = b"\x00" * 1536
    chunk.embed_model = "x"
    db.commit()
    assert _match(db, "photosynthesis") == [chunk.id]
    db.execute(text("INSERT INTO chunk_fts(chunk_fts) VALUES('integrity-check')"))


def test_fts_follows_delete(db: Session, chunk: Chunk) -> None:
    db.delete(chunk)
    db.commit()
    assert _match(db, "photosynthesis") == []


def test_fts_follows_cascade_delete(db: Session, chunk: Chunk) -> None:
    db.execute(text("DELETE FROM material"))
    db.commit()
    assert db.execute(text("SELECT count(*) FROM chunk")).scalar() == 0
    assert _match(db, "photosynthesis") == []


def test_check_constraint_rejects_bad_kind(db: Session, chunk: Chunk) -> None:
    db.add(Chunk(material_id=chunk.material_id, position=1, kind="video", text="x"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_app_has_session_factory(client, settings: Settings) -> None:
    assert isinstance(client.app.state.session_factory, sessionmaker)
    assert settings.database_url.endswith("learnmate.db")
