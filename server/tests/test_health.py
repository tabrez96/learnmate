from pathlib import Path

from fastapi.testclient import TestClient

from learnmate.config import Settings


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_makes_data_dir(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    assert settings.data_dir.is_dir()
    assert settings.data_dir.is_relative_to(tmp_path)
