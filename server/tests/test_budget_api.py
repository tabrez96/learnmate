import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from learnmate.llm.budget import REACHED_MESSAGE, BudgetReached, BudgetStatus
from learnmate.llm.types import Passage


def test_get_budget_empty(client: TestClient) -> None:
    body = client.get("/api/v1/budget").json()
    assert body["spent_usd"] == 0
    assert body["budget_usd"] == 10.0
    assert body["reached"] is False
    assert re.fullmatch(r"\d{4}-\d{2}", body["month"])


def test_get_budget_after_calls(app: FastAPI, client: TestClient) -> None:
    passages = [Passage(id=1, text="t", material="m", chapter="c")]
    for _ in range(2):
        app.state.llm.build_lesson("t", passages=passages, grade=6)
    assert client.get("/api/v1/budget").json()["spent_usd"] == 0.0021


def test_get_budget_needs_token(app: FastAPI) -> None:
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/v1/budget").status_code == 401


def test_budget_reached_error_shape(app: FastAPI, client: TestClient) -> None:
    @app.get("/api/v1/test-budget-reached")
    def raise_reached() -> None:
        raise BudgetReached(BudgetStatus("2026-01", 10, 10, True))  # type: ignore[arg-type]

    response = client.get("/api/v1/test-budget-reached")
    assert response.status_code == 409
    assert response.json() == {"error": "budget_reached", "detail": REACHED_MESSAGE}
