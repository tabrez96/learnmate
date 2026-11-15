from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from learnmate.config import Settings
from learnmate.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", device_token="test-device-token")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c
