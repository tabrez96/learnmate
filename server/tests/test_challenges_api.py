import datetime as dt
import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.api.family import FAMILY_ID
from learnmate.clock import FakeClock
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import LlmResult, QuestionSet
from learnmate.models import (
    Chapter,
    Chunk,
    Family,
    Material,
    Outbox,
    Points,
    Question,
    SessionChapter,
    StudySession,
    StudyTest,
    Subject,
)

API = "/api/v1"
MON = dt.datetime(2026, 1, 5, 9, 0)
TUE = dt.datetime(2026, 1, 6, 9, 0)
BAD = 999999


class Spy(FakeLlm):
    def __init__(self, settings, bad: int = 0, always_bad: bool = False):
        super().__init__(settings)
        self.bad = bad
        self.always_bad = always_bad
        self.batches = 0
        self.made = 0

    def generate_questions(self, *, passages, count, grade) -> LlmResult[QuestionSet]:
        first = self.batches == 0
        self.batches += 1
        result = super().generate_questions(passages=passages, count=count, grade=grade)
        for i, q in enumerate(result.value.questions):
            self.made += 1
            q.prompt = f"Prompt {self.made}?"
            if self.always_bad or (first and i < self.bad):
                q.passage_id = BAD
        return result


def _material(db, subject: Subject, title: str, names: tuple[str, ...]):
    material = Material(subject_id=subject.id, title=title, kind="upload")
    db.add(material)
    db.flush()
    chapters = [
        Chapter(material_id=material.id, name=n, position=i)
        for i, n in enumerate(names)
    ]
    db.add_all(chapters)
    db.flush()
    ids: dict[str, list[int]] = {}
    position = 0
    for c in chapters:
        ids[c.name] = []
        for n in range(3):
            chunk = Chunk(
                material_id=material.id,
                chapter_id=c.id,
                page=position + 1,
                position=position,
                text=f"{c.name} passage {n}.",
            )
            db.add(chunk)
            db.flush()
            ids[c.name].append(chunk.id)
            position += 1
    return chapters, ids


def _setup(
    client: TestClient,
    *,
    earlier: bool = True,
    other_subject_earlier: bool = False,
    state: str = "running",
) -> tuple[int, dict[str, list[int]]]:
    client.app.state.clock = FakeClock(TUE)
    with client.app.state.session_factory() as db:
        db.add(Family(id=FAMILY_ID, child_name="Sam", grade=6))
        subject = Subject(name="Science", icon="flask")
        other = Subject(name="History", icon="book")
        db.add_all([subject, other])
        db.flush()
        chapters, ids = _material(db, subject, "Plants", ("Roots", "Leaves"))
        other_chapters, other_ids = _material(db, other, "Rome", ("Forum",))
        ids.update(other_ids)
        if earlier:
            old = StudySession(
                subject_id=subject.id,
                type="learn",
                question_count=5,
                state="ended",
                started_at=MON,
            )
            db.add(old)
            db.flush()
            db.add(SessionChapter(session_id=old.id, chapter_id=chapters[0].id))
        if other_subject_earlier:
            old = StudySession(
                subject_id=other.id,
                type="learn",
                question_count=5,
                state="ended",
                started_at=MON,
            )
            db.add(old)
            db.flush()
            db.add(SessionChapter(session_id=old.id, chapter_id=other_chapters[0].id))
        row = StudySession(
            subject_id=subject.id,
            type="learn",
            question_count=5,
            state=state,
            started_at=TUE if state != "set_up" else None,
        )
        db.add(row)
        db.flush()
        db.add(SessionChapter(session_id=row.id, chapter_id=chapters[1].id))
        db.commit()
        return row.id, ids


def _spy(client: TestClient, **kwargs) -> Spy:
    spy = Spy(client.app.state.settings, **kwargs)
    client.app.state.llm.inner = spy
    return spy


def _create(client: TestClient, session_id: int, kind: str):
    return client.post(f"{API}/sessions/{session_id}/challenges", json={"kind": kind})


def _run(client: TestClient, test_id: int, picks: list[int]) -> dict:
    """Answer in order; option 0 is the right one."""
    body: dict = {}
    for position, option in enumerate(picks):
        r = client.post(
            f"{API}/tests/{test_id}/answers",
            json={"position": position, "answer_index": option},
        )
        assert r.status_code == 200
        body = r.json()
    return body


def _chunks_of(client: TestClient, test_id: int) -> set[int]:
    with client.app.state.session_factory() as db:
        return set(
            db.scalars(select(Question.chunk_id).where(Question.test_id == test_id))
        )


def _finish_graded_test(client: TestClient, session_id: int) -> None:
    r = client.post(f"{API}/sessions/{session_id}/tests")
    assert r.status_code == 200
    _run(client, r.json()["id"], [0] * r.json()["total"])


def test_warmup_uses_earlier_chapters(client: TestClient) -> None:
    session_id, ids = _setup(client)
    _spy(client)
    body = _create(client, session_id, "warmup").json()
    assert body["total"] == 3
    assert body["kind"] == "warmup"
    assert _chunks_of(client, body["id"]) <= set(ids["Roots"])


def test_warmup_falls_back_to_own_chapters(client: TestClient) -> None:
    session_id, ids = _setup(client, earlier=False)
    _spy(client)
    body = _create(client, session_id, "warmup").json()
    assert _chunks_of(client, body["id"]) <= set(ids["Leaves"])


def test_earlier_session_of_other_subject_is_ignored(client: TestClient) -> None:
    session_id, ids = _setup(client, earlier=False, other_subject_earlier=True)
    _spy(client)
    body = _create(client, session_id, "warmup").json()
    used = _chunks_of(client, body["id"])
    assert used <= set(ids["Leaves"])
    assert not used & set(ids["Forum"])


def test_challenge_questions_stay_inside_subject(client: TestClient) -> None:
    session_id, ids = _setup(client, other_subject_earlier=True)
    _finish_graded_test(client, session_id)
    spy = _spy(client, bad=2)
    body = _create(client, session_id, "bonus").json()
    assert spy.batches >= 2  # the first bonus batch cited a passage outside the scope
    allowed = set(ids["Roots"]) | set(ids["Leaves"])
    assert _chunks_of(client, body["id"]) <= allowed


def test_challenge_gives_up_on_bad_citations(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client, always_bad=True)
    assert _create(client, session_id, "challenge").status_code == 502


def test_warmup_points_and_step(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    created = _create(client, session_id, "warmup").json()
    body = _run(client, created["id"], [0, 0, 1])
    assert body["finished"] is True
    assert body["test"]["points_so_far"] == 20
    assert body["test"]["result"] is None
    with client.app.state.session_factory() as db:
        test = db.get(StudyTest, created["id"])
        assert (test.status, test.graded, test.band) == ("done", False, None)
        rows = list(db.scalars(select(Points)))
        assert [(p.reason, p.amount) for p in rows] == [("warmup", 20)]
        plan = json.loads(db.get(StudySession, session_id).plan_json)
        assert (
            next(s for s in plan["steps"] if s["key"] == "warmup")["status"] == "done"
        )


def test_challenge_points(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    created = _create(client, session_id, "challenge").json()
    assert created["total"] == 1
    _run(client, created["id"], [0])
    with client.app.state.session_factory() as db:
        rows = list(db.scalars(select(Points)))
        assert [(p.reason, p.amount) for p in rows] == [("challenge", 10)]


def test_all_wrong_gives_no_points_but_completes(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    created = _create(client, session_id, "challenge").json()
    _run(client, created["id"], [1])
    with client.app.state.session_factory() as db:
        assert db.query(Points).count() == 0
        assert db.get(StudyTest, created["id"]).status == "done"


def test_bonus_requires_finished_test(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    assert _create(client, session_id, "bonus").status_code == 409
    _finish_graded_test(client, session_id)
    r = _create(client, session_id, "bonus")
    assert r.status_code == 200
    assert r.json()["total"] == 3
    _run(client, r.json()["id"], [0, 0, 0])
    with client.app.state.session_factory() as db:
        bonus = db.scalars(select(Points).where(Points.reason == "bonus")).all()
        assert [p.amount for p in bonus] == [30]


def test_challenges_never_send_a_grade(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    _finish_graded_test(client, session_id)
    with client.app.state.session_factory() as db:
        before = db.query(Outbox).count()
        plan_before = db.get(StudySession, session_id).plan_json
    ids = []
    for kind in ("warmup", "challenge", "bonus"):
        created = _create(client, session_id, kind).json()
        _run(client, created["id"], [0] * created["total"])
        ids.append(created["id"])
    with client.app.state.session_factory() as db:
        assert db.query(Outbox).count() == before
        assert all(db.get(StudyTest, i).band is None for i in ids)
        plan = json.loads(db.get(StudySession, session_id).plan_json)
        test_step = next(s for s in plan["steps"] if s["key"] == "test")
        old = next(s for s in json.loads(plan_before)["steps"] if s["key"] == "test")
        assert test_step == old


def test_create_is_idempotent(client: TestClient) -> None:
    session_id, _ = _setup(client)
    spy = _spy(client)
    first = _create(client, session_id, "challenge").json()
    second = _create(client, session_id, "challenge").json()
    assert first["id"] == second["id"]
    assert spy.batches == 1


def test_warmup_after_step_finished(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    r = client.patch(
        f"{API}/sessions/{session_id}/plan/steps/warmup", json={"status": "skipped"}
    )
    assert r.status_code == 200
    assert _create(client, session_id, "warmup").status_code == 409


def test_not_running(client: TestClient) -> None:
    session_id, _ = _setup(client, state="set_up")
    _spy(client)
    assert _create(client, session_id, "warmup").status_code == 409
    assert _create(client, 12345, "warmup").status_code == 404
    assert _create(client, session_id, "boss").status_code == 422


def test_progress_badges_count_challenges(client: TestClient) -> None:
    session_id, _ = _setup(client)
    _spy(client)
    before = client.get(f"{API}/progress").json()
    assert before["completed_challenges"] == 0
    created = _create(client, session_id, "challenge").json()
    _run(client, created["id"], [0])
    body = client.get(f"{API}/progress").json()
    assert "first_challenge" in body["badges"]
    assert body["completed_challenges"] == 1
    assert body["badge_count"] == len(body["badges"])
