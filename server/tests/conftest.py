import datetime as dt
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from learnmate.clock import FakeClock
from learnmate.config import Settings
from learnmate.db import create_db_engine, make_session_factory
from learnmate.main import create_app
from learnmate.models import StudySession, Subject

SERVER_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", device_token="test-device-token")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def alembic_config(tmp_path: Path) -> Config:
    cfg = Config(str(SERVER_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'test.db'}")
    return cfg


@pytest.fixture
def engine(alembic_config: Config) -> Iterator[Engine]:
    command.upgrade(alembic_config, "head")
    eng = create_db_engine(alembic_config.get_main_option("sqlalchemy.url"))
    yield eng
    eng.dispose()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(dt.datetime(2026, 1, 5, 9, 0))


@pytest.fixture
def db(engine: Engine, clock: FakeClock) -> Iterator[Session]:
    with make_session_factory(engine, clock)() as session:
        yield session


@pytest.fixture
def study_session(db: Session) -> StudySession:
    subject = Subject(name="Science", icon="flask")
    db.add(subject)
    db.flush()
    row = StudySession(subject_id=subject.id, type="learn", question_count=5)
    db.add(row)
    db.flush()
    return row
