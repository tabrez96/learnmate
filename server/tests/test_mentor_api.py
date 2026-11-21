import datetime as dt
import json
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.api.family import FAMILY_ID
from learnmate.clock import FakeClock
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import (
    Lesson,
    LlmResult,
    LlmUnavailableError,
    Passage,
    Usage,
    model_for,
)
from learnmate.mentor import service
from learnmate.mentor.lesson import lesson_step
from learnmate.models import (
    Chapter,
    Chunk,
    Family,
    LlmUsage,
    Material,
    Points,
    SessionChapter,
    StudySession,
    Subject,
)
from learnmate.plan import service as plan_service

API = "/api/v1"
MON = dt.datetime(2026, 1, 5, 9, 0)
BAD = 999999


class Spy(FakeLlm):
    def __init__(self, settings, bad_calls: int = 0) -> None:
        super().__init__(settings)
        self.bad_calls = bad_calls
        self.sent: list[list[Passage]] = []

    def build_lesson(self, topic, *, passages, grade) -> LlmResult[Lesson]:
        self.sent.append(passages)
        result = super().build_lesson(topic, passages=passages, grade=grade)
        if len(self.sent) <= self.bad_calls:
            result.value.steps[0].passage_ids = [BAD]
        return result


def _setup(
    client: TestClient,
    *,
    type: str = "learn",
    state: str = "running",
    chapter: str = "Roots",
    chunks: bool = True,
) -> tuple[int, dict[str, list[int]]]:
    client.app.state.clock = FakeClock(MON)
    ids: dict[str, list[int]] = {}
    with client.app.state.session_factory() as db:
        if db.get(Family, FAMILY_ID) is None:
            db.add(Family(id=FAMILY_ID, child_name="Sam", grade=6))
        subject = Subject(name="Science", icon="flask")
        db.add(subject)
        db.flush()
        material = Material(subject_id=subject.id, title="Plants", kind="upload")
        db.add(material)
        db.flush()
        chapters = {
            name: Chapter(material_id=material.id, name=name, position=i)
            for i, name in enumerate(("Roots", "Leaves"))
        }
        db.add_all(chapters.values())
        db.flush()
        position = 0
        for name, c in chapters.items():
            ids[name] = []
            if not chunks and name == chapter:
                continue
            for n in range(3):
                chunk = Chunk(
                    material_id=material.id,
                    chapter_id=c.id,
                    page=position + 1,
                    position=position,
                    text=f"{name} passage {n}.",
                )
                db.add(chunk)
                db.flush()
                ids[name].append(chunk.id)
                position += 1
        row = StudySession(
            subject_id=subject.id,
            type=type,
            question_count=5,
            state=state,
            started_at=MON if state == "running" else None,
        )
        db.add(row)
        db.flush()
        db.add(SessionChapter(session_id=row.id, chapter_id=chapters[chapter].id))
        db.commit()
        return row.id, ids


def _spy(client: TestClient, bad_calls: int = 0) -> Spy:
    spy = Spy(client.app.state.settings, bad_calls)
    client.app.state.llm.inner = spy
    return spy


def _lesson_url(session_id: int) -> str:
    return f"{API}/sessions/{session_id}/mentor/lesson"


def _answer(client: TestClient, session_id: int, index: int, answer: int):
    url = f"{_lesson_url(session_id)}/steps/{index}/answer"
    return client.post(url, json={"answer_index": answer})


def _exhaust_budget(client: TestClient) -> None:
    with client.app.state.session_factory() as db:
        db.add(
            LlmUsage(
                at=MON,
                model="m",
                purpose="lesson",
                cost_usd=Decimal(10),
            )
        )
        db.commit()


def test_lesson_with_fake_llm_end_to_end(client: TestClient) -> None:
    session_id, ids = _setup(client)
    r = client.post(_lesson_url(session_id))
    assert r.status_code == 200
    body = r.json()
    assert len(body["steps"]) >= 1
    for step in body["steps"]:
        assert {s["passage_id"] for s in step["sources"]} <= set(ids["Roots"])
        assert step["check"]["correct_index"] is None
        assert step["check"]["explanation"] is None
    assert client.get(f"{API}/sessions/{session_id}/plan").status_code == 200
    with client.app.state.session_factory() as db:
        rows = db.scalars(select(LlmUsage).where(LlmUsage.purpose == "lesson")).all()
        assert len(rows) == 1


def test_lesson_is_stored_and_not_rebuilt(client: TestClient) -> None:
    session_id, _ = _setup(client)
    spy = _spy(client)
    first = client.post(_lesson_url(session_id))
    second = client.post(_lesson_url(session_id))
    assert second.status_code == 200
    assert second.json() == first.json()
    assert spy.calls.count("lesson") == 1


def test_invalid_citation_retried_once_then_ok(client: TestClient) -> None:
    session_id, _ = _setup(client)
    spy = _spy(client, bad_calls=1)
    r = client.post(_lesson_url(session_id))
    assert r.status_code == 200
    assert len(spy.sent) == 2


def test_invalid_citation_twice_rejected(client: TestClient) -> None:
    session_id, _ = _setup(client)
    spy = _spy(client, bad_calls=5)
    r = client.post(_lesson_url(session_id))
    assert r.status_code == 502
    assert len(spy.sent) == 2
    with client.app.state.session_factory() as db:
        row = db.get(StudySession, session_id)
        assert row.plan_json is None or '"lesson": {' not in row.plan_json


def test_recap_uses_chosen_chapter_only(client: TestClient) -> None:
    session_id, ids = _setup(client, type="recap", chapter="Roots")
    spy = _spy(client)
    assert client.post(_lesson_url(session_id)).status_code == 200
    assert spy.sent
    assert {p.chapter for p in spy.sent[0]} == {"Roots"}
    assert {p.id for p in spy.sent[0]} == set(ids["Roots"])


def test_correct_quick_check_writes_points(client: TestClient) -> None:
    session_id, _ = _setup(client)
    client.post(_lesson_url(session_id))
    r = _answer(client, session_id, 0, 0)
    assert r.status_code == 200
    assert r.json()["correct"] is True
    assert r.json()["points_awarded"] == 10
    assert client.get(f"{API}/progress").json()["points"] == 10
    with client.app.state.session_factory() as db:
        rows = db.scalars(select(Points)).all()
        assert [(p.reason, p.amount) for p in rows] == [("quick_check", 10)]
    shown = client.post(_lesson_url(session_id)).json()["steps"][0]["check"]
    assert shown["answer_index"] == 0
    assert shown["correct_index"] == 0


def test_wrong_quick_check_no_points(client: TestClient) -> None:
    session_id, _ = _setup(client)
    client.post(_lesson_url(session_id))
    r = _answer(client, session_id, 0, 3)
    assert r.json()["correct"] is False
    assert r.json()["points_awarded"] == 0
    with client.app.state.session_factory() as db:
        assert db.scalars(select(Points)).all() == []
    assert _answer(client, session_id, 0, 0).status_code == 409


def test_answer_errors(client: TestClient) -> None:
    session_id, _ = _setup(client)
    assert _answer(client, session_id, 0, 0).status_code == 409  # not started
    client.post(_lesson_url(session_id))
    assert _answer(client, session_id, 7, 0).status_code == 404
    assert _answer(client, session_id, 0, 4).status_code == 422
    assert _answer(client, 9999, 0, 0).status_code == 404


def test_budget_reached_blocks_new_lesson(client: TestClient) -> None:
    session_id, _ = _setup(client)
    spy = _spy(client)
    _exhaust_budget(client)
    r = client.post(_lesson_url(session_id))
    assert r.status_code == 409
    assert r.json()["error"] == "budget_reached"
    assert spy.sent == []


def test_started_lesson_survives_budget_reached(client: TestClient) -> None:
    session_id, _ = _setup(client)
    first = client.post(_lesson_url(session_id))
    _exhaust_budget(client)
    again = client.post(_lesson_url(session_id))
    assert again.status_code == 200
    assert again.json() == first.json()
    assert _answer(client, session_id, 0, 0).status_code == 200


def test_test_only_session_has_no_lesson(client: TestClient) -> None:
    session_id, _ = _setup(client, type="test_only")
    r = client.post(_lesson_url(session_id))
    assert r.status_code == 409
    assert r.json()["detail"] == "This session has no lesson"


def test_lesson_needs_running_session(client: TestClient) -> None:
    session_id, _ = _setup(client, state="set_up")
    assert client.post(_lesson_url(session_id)).status_code == 409
    assert client.post(_lesson_url(9999)).status_code == 404


def test_empty_scope(client: TestClient) -> None:
    session_id, _ = _setup(client, chunks=False)
    spy = _spy(client)
    assert client.post(_lesson_url(session_id)).status_code == 422
    assert spy.sent == []


def test_model_failure_is_502(client: TestClient) -> None:
    settings = client.app.state.settings
    usage = Usage(model_for(settings, "lesson"), "lesson")

    class Broken(FakeLlm):
        def build_lesson(self, topic, *, passages, grade):
            raise LlmUnavailableError("down", usage)

    session_id, _ = _setup(client)
    client.app.state.llm.inner = Broken(settings)
    assert client.post(_lesson_url(session_id)).status_code == 502


class TwoSteps(Spy):
    def build_lesson(self, topic, *, passages, grade) -> LlmResult[Lesson]:
        result = super().build_lesson(topic, passages=passages, grade=grade)
        result.value.steps.append(result.value.steps[0].model_copy(deep=True))
        return result


def _race(client: TestClient, monkeypatch, session_id: int, rival_index: int) -> None:
    """Make a rival answer land between the read and the save of the next answer."""
    original = service.answer_check
    fired = []

    def racing(plan, index, answer_index):
        if not fired:
            fired.append(True)
            with client.app.state.session_factory() as db:
                service.answer(
                    db,
                    client.app.state.settings,
                    client.app.state.clock,
                    session_id,
                    rival_index,
                    0,
                )
        return original(plan, index, answer_index)

    monkeypatch.setattr(service, "answer_check", racing)


def test_double_answer_awards_points_once(client: TestClient, monkeypatch) -> None:
    session_id, _ = _setup(client)
    client.post(_lesson_url(session_id))
    _race(client, monkeypatch, session_id, rival_index=0)
    assert _answer(client, session_id, 0, 0).status_code == 409
    with client.app.state.session_factory() as db:
        assert len(db.scalars(select(Points)).all()) == 1


def test_answers_to_two_steps_both_kept(client: TestClient, monkeypatch) -> None:
    session_id, _ = _setup(client)
    client.app.state.llm.inner = TwoSteps(client.app.state.settings)
    client.post(_lesson_url(session_id))
    _race(client, monkeypatch, session_id, rival_index=1)
    assert _answer(client, session_id, 0, 0).status_code == 200
    steps = client.post(_lesson_url(session_id)).json()["steps"]
    assert [s["check"]["answer_index"] for s in steps] == [0, 0]
    with client.app.state.session_factory() as db:
        assert len(db.scalars(select(Points)).all()) == 2


def test_patch_step_keeps_concurrent_answer(client: TestClient, monkeypatch) -> None:
    session_id, _ = _setup(client)
    client.post(_lesson_url(session_id))
    original = plan_service.set_step_status
    fired = []

    def racing(plan, key, status):
        if not fired:
            fired.append(True)
            with client.app.state.session_factory() as db:
                service.answer(
                    db,
                    client.app.state.settings,
                    client.app.state.clock,
                    session_id,
                    0,
                    0,
                )
        return original(plan, key, status)

    monkeypatch.setattr(plan_service, "set_step_status", racing)
    response = client.patch(
        f"/api/v1/sessions/{session_id}/plan/steps/warmup", json={"status": "done"}
    )
    assert response.status_code == 200
    plan = client.get(f"/api/v1/sessions/{session_id}/plan").json()
    assert [s["status"] for s in plan["steps"] if s["key"] == "warmup"] == ["done"]
    assert _answer(client, session_id, 0, 0).status_code == 409


def test_get_plan_keeps_concurrently_saved_plan(
    client: TestClient, monkeypatch
) -> None:
    session_id, _ = _setup(client)
    original = plan_service.build_plan
    stored: dict = {}

    def racing(plan_input):
        plan = original(plan_input)
        saved = json.loads(json.dumps(plan))
        lesson_step(saved)["lesson"] = {"steps": []}
        stored.update(saved)
        with client.app.state.session_factory() as db:
            db.get(StudySession, session_id).plan_json = json.dumps(saved)
            db.commit()
        return plan

    monkeypatch.setattr(plan_service, "build_plan", racing)
    with client.app.state.session_factory() as db:
        got = plan_service.get_plan(
            db, client.app.state.settings, client.app.state.clock, session_id
        )
    assert got == stored
    with client.app.state.session_factory() as db:
        assert json.loads(db.get(StudySession, session_id).plan_json) == stored
