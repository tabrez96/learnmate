import datetime as dt
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.models import (
    Chapter,
    Family,
    LlmUsage,
    Material,
    Outbox,
    SessionChapter,
    SessionEvent,
    SessionMaterial,
    StudySession,
)
from learnmate.sessions.pins import verify_pin
from learnmate.telegram.links import handle_new_pin
from learnmate.telegram.templates import NEW_PIN_SENT, NEW_PIN_UNAVAILABLE

API = "/api/v1"


def _material(app: FastAPI, subject_id: int) -> tuple[int, list[int]]:
    with app.state.session_factory() as db:
        material = Material(
            subject_id=subject_id, title="Plants", kind="upload", status="ready"
        )
        db.add(material)
        db.flush()
        chapters = [
            Chapter(material_id=material.id, name=f"Chapter {i}", position=i)
            for i in (1, 2)
        ]
        db.add_all(chapters)
        db.commit()
        return material.id, [c.id for c in chapters]


def _setup(client: TestClient, app: FastAPI) -> dict:
    client.put(f"{API}/family", json={"child_name": "Sam", "grade": 6})
    subject = client.post(f"{API}/subjects", json={"name": "Science"}).json()
    material_id, chapter_ids = _material(app, subject["id"])
    return {"subject": subject["id"], "material": material_id, "chapters": chapter_ids}


def _create(client: TestClient, ctx: dict, **overrides):
    body = {
        "subject_id": ctx["subject"],
        "type": "learn",
        "material_ids": [ctx["material"]],
        "chapter_ids": [],
        "question_count": 10,
    } | overrides
    return client.post(f"{API}/sessions", json=body)


def _row(app: FastAPI, session_id: int) -> StudySession:
    with app.state.session_factory() as db:
        row = db.get(StudySession, session_id)
        db.expunge(row)
        return row


def _outbox(app: FastAPI) -> list[Outbox]:
    with app.state.session_factory() as db:
        return list(db.scalars(select(Outbox).order_by(Outbox.id)))


def _events(app: FastAPI, session_id: int, type_: str) -> list[dict]:
    with app.state.session_factory() as db:
        rows = db.scalars(
            select(SessionEvent).where(
                SessionEvent.session_id == session_id, SessionEvent.type == type_
            )
        )
        return [json.loads(r.data_json) if r.data_json else {} for r in rows]


def test_create_returns_pin_once_and_queues_telegram(
    client: TestClient, app: FastAPI
) -> None:
    ctx = _setup(client, app)
    response = _create(client, ctx, chapter_ids=ctx["chapters"])
    assert response.status_code == 201
    body = response.json()
    assert len(body["pin"]) == 4 and body["pin"].isdigit()
    assert body["state"] == "set_up"
    assert body["material_ids"] == [ctx["material"]]
    assert body["chapter_ids"] == sorted(ctx["chapters"])
    (message,) = _outbox(app)
    assert body["pin"] in message.text
    assert f"new_pin:{body['id']}" in message.buttons_json
    row = _row(app, body["id"])
    assert row.pin_hash.startswith("$argon2")
    assert row.pin_enc != body["pin"]


def test_pin_not_in_other_responses(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    current = client.get(f"{API}/sessions/current")
    started = client.post(f"{API}/sessions/{created['id']}/start")
    expected = set(created) - {"pin"}
    for response in (current, started):
        assert set(response.json()) == expected


def test_replace_pin_old_stops_working(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    first = _create(client, ctx).json()
    second = client.post(f"{API}/sessions/{first['id']}/pin")
    assert second.status_code == 200
    pin2 = second.json()["pin"]
    assert pin2 != first["pin"]
    assert second.json()["pin_version"] == 2
    row = _row(app, first["id"])
    assert verify_pin(row, first["pin"]) is False
    assert verify_pin(row, pin2) is True
    assert _events(app, first["id"], "pin_replaced") == [
        {"pin_version": 2, "via": "app"}
    ]
    newest = _outbox(app)[-1]
    assert pin2 in newest.text and "old PIN no longer works" in newest.text


def test_replace_pin_refused_for_cancelled_session(
    client: TestClient, app: FastAPI
) -> None:
    ctx = _setup(client, app)
    first = _create(client, ctx).json()
    _create(client, ctx)
    assert client.post(f"{API}/sessions/{first['id']}/pin").status_code == 409
    assert client.post(f"{API}/sessions/999/pin").status_code == 404


def test_telegram_new_pin_replaces(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    with app.state.session_factory() as db:
        db.get(Family, 1).telegram_chat_id = 42
        db.commit()
        reply = handle_new_pin(
            db, app.state.telegram_hooks, 42, f"new_pin:{created['id']}"
        )
    assert reply == NEW_PIN_SENT
    row = _row(app, created["id"])
    assert row.pin_version == 2
    assert verify_pin(row, created["pin"]) is False
    assert _events(app, created["id"], "pin_replaced")[0]["via"] == "telegram"


def test_telegram_new_pin_unavailable_for_cancelled(
    client: TestClient, app: FastAPI
) -> None:
    ctx = _setup(client, app)
    first = _create(client, ctx).json()
    _create(client, ctx)
    with app.state.session_factory() as db:
        db.get(Family, 1).telegram_chat_id = 42
        db.commit()
        reply = handle_new_pin(
            db, app.state.telegram_hooks, 42, f"new_pin:{first['id']}"
        )
    assert reply == NEW_PIN_UNAVAILABLE


def test_create_cancels_older_set_up(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    first = _create(client, ctx).json()
    second = _create(client, ctx).json()
    row = _row(app, first["id"])
    assert row.state == "cancelled"
    assert row.pin_hash is None and row.pin_enc is None
    assert client.get(f"{API}/sessions/current").json()["id"] == second["id"]


def test_create_refused_while_running(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    client.post(f"{API}/sessions/{created['id']}/start")
    assert _create(client, ctx).status_code == 409


def test_scope_rows_written(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    created = _create(client, ctx, chapter_ids=ctx["chapters"][:1]).json()
    with app.state.session_factory() as db:
        materials = db.scalars(select(SessionMaterial)).all()
        chapters = db.scalars(select(SessionChapter)).all()
    assert [(m.session_id, m.material_id) for m in materials] == [
        (created["id"], ctx["material"])
    ]
    assert [(c.session_id, c.chapter_id) for c in chapters] == [
        (created["id"], ctx["chapters"][0])
    ]


def test_duplicate_ids_are_deduped(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    response = _create(client, ctx, material_ids=[ctx["material"]] * 2)
    assert response.status_code == 201
    assert response.json()["material_ids"] == [ctx["material"]]


@pytest.mark.parametrize("kind", ["recap", "test_only"])
def test_recap_and_test_only_need_a_chapter(
    client: TestClient, app: FastAPI, kind: str
) -> None:
    ctx = _setup(client, app)
    assert _create(client, ctx, type=kind).status_code == 422
    assert (
        _create(client, ctx, type=kind, chapter_ids=ctx["chapters"]).status_code == 201
    )


def test_learn_needs_material_or_chapter(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    assert _create(client, ctx, material_ids=[]).status_code == 422


def test_unknown_subject_rejected(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    assert _create(client, ctx, subject_id=999).status_code == 422


def test_ids_from_other_subject_rejected(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    other = client.post(f"{API}/subjects", json={"name": "History"}).json()
    _, other_chapters = _material(app, other["id"])
    assert _create(client, ctx, chapter_ids=other_chapters[:1]).status_code == 422
    assert _create(client, ctx, material_ids=[12345]).status_code == 422


def test_question_count_limited(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    assert _create(client, ctx, question_count=7).status_code == 422


def test_budget_reached_blocks_create(client: TestClient, app: FastAPI) -> None:
    ctx = _setup(client, app)
    with app.state.session_factory() as db:
        db.add(
            LlmUsage(
                at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
                model="claude-sonnet-5-5",
                purpose="lesson",
                input_tokens=0,
                output_tokens=0,
                web_searches=0,
                cost_usd=app.state.settings.llm_monthly_budget_usd,
            )
        )
        db.commit()
    response = _create(client, ctx)
    assert response.status_code == 409
    assert response.json()["error"] == "budget_reached"
    with app.state.session_factory() as db:
        assert db.scalars(select(StudySession)).first() is None


def test_start_sets_running_and_tells_telegram(
    client: TestClient, app: FastAPI
) -> None:
    ctx = _setup(client, app)
    created = _create(client, ctx).json()
    response = client.post(f"{API}/sessions/{created['id']}/start")
    assert response.status_code == 200
    assert response.json()["state"] == "running"
    assert response.json()["started_at"] is not None
    assert _events(app, created["id"], "started") == [{}]
    text = _outbox(app)[-1].text
    assert "started a" in text and "Science" in text
    assert client.post(f"{API}/sessions/{created['id']}/start").status_code == 409
    assert client.post(f"{API}/sessions/999/start").status_code == 404


def test_current_404_when_none(client: TestClient) -> None:
    assert client.get(f"{API}/sessions/current").status_code == 404


def test_family_required(client: TestClient) -> None:
    response = client.post(
        f"{API}/sessions", json={"subject_id": 1, "type": "learn", "material_ids": [1]}
    )
    assert response.status_code == 409
