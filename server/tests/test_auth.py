from fastapi import FastAPI
from fastapi.testclient import TestClient

from learnmate.config import Settings
from learnmate.main import create_app


def test_health_needs_no_token(app: FastAPI) -> None:
    assert TestClient(app).get("/api/v1/health").status_code == 200


def test_missing_token_is_401(app: FastAPI) -> None:
    assert TestClient(app).get("/api/v1/family").status_code == 401


def test_wrong_token_is_401(app: FastAPI) -> None:
    response = TestClient(app).get(
        "/api/v1/family", headers={"Authorization": "Bearer nope"}
    )
    assert response.status_code == 401


def test_lowercase_scheme_is_401(app: FastAPI) -> None:
    response = TestClient(app).get(
        "/api/v1/family", headers={"Authorization": "bearer test-device-token"}
    )
    assert response.status_code == 401


def test_health_with_trailing_slash_is_not_public(app: FastAPI) -> None:
    assert TestClient(app).get("/api/v1/health/").status_code == 401


def test_right_token_passes(app: FastAPI) -> None:
    response = TestClient(app).get(
        "/api/v1/family", headers={"Authorization": "Bearer test-device-token"}
    )
    assert response.status_code == 404


def test_empty_configured_token_rejects_everything(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"device_token": ""}))
    try:
        response = TestClient(app).get(
            "/api/v1/family", headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401
    finally:
        app.state.engine.dispose()
