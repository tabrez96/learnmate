from fastapi import FastAPI
from fastapi.testclient import TestClient

from learnmate.models import Family
from learnmate.passwords import verify_password

SETUP = {"child_name": "Omar", "grade": 7}


def _family(app: FastAPI) -> Family:
    with app.state.session_factory() as db:
        family = db.get(Family, 1)
        assert family is not None
        return family


def test_get_before_setup_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/family").status_code == 404


def test_put_then_get_uses_defaults(client: TestClient) -> None:
    assert client.put("/api/v1/family", json=SETUP).status_code == 200
    body = client.get("/api/v1/family").json()
    assert body["child_name"] == "Omar"
    assert body["grade"] == 7
    assert body["inactivity_warn_s"] == 240
    assert body["inactivity_lock_s"] == 300
    assert body["outside_books_allowed"] is True
    assert body["telegram_connected"] is False
    assert body["fallback_set"] is False


def test_put_round_trips_all_fields(client: TestClient) -> None:
    payload = {
        "child_name": "Mia",
        "grade": 9,
        "outside_books_allowed": False,
        "inactivity_warn_s": 100,
        "inactivity_lock_s": 150,
    }
    client.put("/api/v1/family", json=payload)
    body = client.get("/api/v1/family").json()
    assert {k: body[k] for k in payload} == payload


def test_name_is_stripped(client: TestClient) -> None:
    client.put("/api/v1/family", json={"child_name": "  Omar ", "grade": 7})
    assert client.get("/api/v1/family").json()["child_name"] == "Omar"


def test_partial_put_keeps_earlier_values(client: TestClient) -> None:
    client.put(
        "/api/v1/family",
        json={**SETUP, "inactivity_warn_s": 120, "inactivity_lock_s": 200},
    )
    client.put("/api/v1/family", json={"child_name": "Omar K", "grade": 8})
    body = client.get("/api/v1/family").json()
    assert body["child_name"] == "Omar K"
    assert body["grade"] == 8
    assert (body["inactivity_warn_s"], body["inactivity_lock_s"]) == (120, 200)


def test_grade_out_of_range_is_422(client: TestClient) -> None:
    for grade in (4, 11):
        response = client.put("/api/v1/family", json={**SETUP, "grade": grade})
        assert response.status_code == 422


def test_warn_not_below_lock_is_422(client: TestClient) -> None:
    client.put("/api/v1/family", json=SETUP)
    response = client.put(
        "/api/v1/family",
        json={**SETUP, "inactivity_warn_s": 300, "inactivity_lock_s": 300},
    )
    assert response.status_code == 422
    body = client.get("/api/v1/family").json()
    assert (body["inactivity_warn_s"], body["inactivity_lock_s"]) == (240, 300)


def test_warn_not_below_lock_on_first_put_saves_nothing(client: TestClient) -> None:
    response = client.put("/api/v1/family", json={**SETUP, "inactivity_warn_s": 400})
    assert response.status_code == 422
    assert client.get("/api/v1/family").status_code == 404


def test_fallback_stored_only_as_argon2id_hash(
    client: TestClient, app: FastAPI
) -> None:
    client.put("/api/v1/family", json=SETUP)
    assert (
        client.put("/api/v1/family/fallback", json={"password": "correct horse"})
    ).status_code == 204
    family = _family(app)
    assert family.fallback_hash is not None
    assert family.fallback_hash.startswith("$argon2id$")
    columns = (c.key for c in Family.__table__.columns)
    assert all("correct horse" not in str(getattr(family, c)) for c in columns)
    assert verify_password("correct horse", family.fallback_hash)
    body = client.get("/api/v1/family").json()
    assert body["fallback_set"] is True
    assert "fallback_hash" not in body


def test_fallback_too_short_is_422(client: TestClient) -> None:
    client.put("/api/v1/family", json=SETUP)
    response = client.put("/api/v1/family/fallback", json={"password": "1234567"})
    assert response.status_code == 422


def test_change_fallback_needs_current_password(
    client: TestClient, app: FastAPI
) -> None:
    client.put("/api/v1/family", json=SETUP)
    client.put("/api/v1/family/fallback", json={"password": "first password"})
    url = "/api/v1/family/fallback"
    assert client.put(url, json={"password": "second password"}).status_code == 403
    wrong = {"password": "second password", "current_password": "nope nope"}
    assert client.put(url, json=wrong).status_code == 403
    right = {"password": "second password", "current_password": "first password"}
    assert client.put(url, json=right).status_code == 204
    assert verify_password("second password", _family(app).fallback_hash)


def test_fallback_before_setup_is_409(client: TestClient) -> None:
    response = client.put("/api/v1/family/fallback", json={"password": "correct horse"})
    assert response.status_code == 409


def test_telegram_code_is_stored_and_replaced(client: TestClient, app: FastAPI) -> None:
    client.put("/api/v1/family", json=SETUP)
    first = client.post("/api/v1/family/telegram-code")
    second = client.post("/api/v1/family/telegram-code")
    assert first.status_code == second.status_code == 201
    codes = [first.json()["code"], second.json()["code"]]
    assert all(len(c) == 16 and int(c, 16) >= 0 for c in codes)
    assert codes[0] != codes[1]
    assert _family(app).telegram_link_code == codes[1]
    assert "telegram_link_code" not in client.get("/api/v1/family").json()


def test_telegram_code_before_setup_is_409(client: TestClient) -> None:
    assert client.post("/api/v1/family/telegram-code").status_code == 409
