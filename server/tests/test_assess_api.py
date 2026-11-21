import datetime as dt
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.api.family import FAMILY_ID
from learnmate.clock import FakeClock
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import LlmResult, QuestionSet
from learnmate.models import (
    Chapter,
    Chunk,
    Exam,
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
    """Questions get unique prompts; `bad` is how many of each call cite a bad passage."""

    def __init__(self, settings, bad: tuple[int, ...] = (), always_bad: bool = False):
        super().__init__(settings)
        self.bad = bad
        self.always_bad = always_bad
        self.counts: list[int] = []
        self.made = 0

    def generate_questions(self, *, passages, count, grade) -> LlmResult[QuestionSet]:
        call = len(self.counts)
        self.counts.append(count)
        result = super().generate_questions(passages=passages, count=count, grade=grade)
        for i, q in enumerate(result.value.questions):
            self.made += 1
            q.prompt = f"Prompt {self.made}?"
            n_bad = self.bad[call] if call < len(self.bad) else 0
            if self.always_bad or i < n_bad:
                q.passage_id = BAD
        return result


def _setup(
    client: TestClient,
    *,
    type: str = "learn",
    state: str = "running",
    daily: bool = False,
    exam: bool = False,
    question_count: int = 5,
) -> tuple[int, dict[str, list[int]]]:
    start = TUE if daily else MON
    client.app.state.clock = FakeClock(start)
    ids: dict[str, list[int]] = {}
    with client.app.state.session_factory() as db:
        db.add(Family(id=FAMILY_ID, child_name="Sam", grade=6))
        subject = Subject(name="Science", icon="flask")
        db.add(subject)
        db.flush()
        material = Material(subject_id=subject.id, title="Plants", kind="upload")
        db.add(material)
        db.flush()
        chapters = [
            Chapter(material_id=material.id, name=name, position=i)
            for i, name in enumerate(("Roots", "Leaves"))
        ]
        db.add_all(chapters)
        db.flush()
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
        if daily:
            db.add(
                StudySession(
                    subject_id=subject.id,
                    type="learn",
                    question_count=5,
                    state="ended",
                    started_at=MON,
                )
            )
        if exam:
            db.add(
                Exam(subject_id=subject.id, date=start.date() + dt.timedelta(days=3))
            )
        row = StudySession(
            subject_id=subject.id,
            type=type,
            question_count=question_count,
            state=state,
            started_at=start if state != "set_up" else None,
        )
        db.add(row)
        db.flush()
        for c in chapters:
            db.add(SessionChapter(session_id=row.id, chapter_id=c.id))
        db.commit()
        return row.id, ids


def _spy(client: TestClient, **kwargs) -> Spy:
    spy = Spy(client.app.state.settings, **kwargs)
    client.app.state.llm.inner = spy
    return spy


def _create(client: TestClient, session_id: int):
    return client.post(f"{API}/sessions/{session_id}/tests")


def _answer(client: TestClient, test_id: int, position: int, option: int):
    return client.post(
        f"{API}/tests/{test_id}/answers",
        json={"position": position, "answer_index": option},
    )


def _run(client: TestClient, test_id: int, picks: list[int]):
    """Answer questions in order; option 0 is the right one."""
    r = None
    for position, option in enumerate(picks):
        r = _answer(client, test_id, position, option)
        assert r.status_code == 200
    return r


def _grade_rows(client: TestClient) -> list[Outbox]:
    with client.app.state.session_factory() as db:
        return list(db.scalars(select(Outbox)))


@pytest.mark.parametrize(
    ("kwargs", "kind", "count"),
    [
        ({"daily": True}, "daily", 5),
        ({}, "weekly", 15),
        ({"exam": True}, "surprise", 8),
        ({"type": "test_only", "question_count": 5}, "test_only", 5),
        ({"type": "test_only", "question_count": 10}, "test_only", 10),
        ({"type": "test_only", "question_count": 15}, "test_only", 15),
    ],
)
def test_question_counts_follow_the_test_kind(
    client: TestClient, kwargs: dict, kind: str, count: int
) -> None:
    session_id, _ = _setup(client, **kwargs)
    _spy(client)
    r = _create(client, session_id)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == kind
    assert body["total"] == count == len(body["questions"])
    with client.app.state.session_factory() as db:
        assert db.query(Question).filter_by(test_id=body["id"]).count() == count


def test_questions_spread_across_scoped_chapters(client: TestClient) -> None:
    session_id, ids = _setup(client, daily=True)
    _spy(client)
    _create(client, session_id)
    with client.app.state.session_factory() as db:
        used = set(db.scalars(select(Question.chunk_id)))
    assert used & set(ids["Roots"])
    assert used & set(ids["Leaves"])


def test_out_of_scope_chunk_ids_are_dropped_and_regenerated(
    client: TestClient,
) -> None:
    session_id, ids = _setup(client, daily=True)
    spy = _spy(client, bad=(2,))
    r = _create(client, session_id)
    assert r.status_code == 200
    assert spy.counts == [5, 2]
    assert r.json()["total"] == 5
    with client.app.state.session_factory() as db:
        chunk_ids = set(db.scalars(select(Question.chunk_id)))
    assert chunk_ids <= set(ids["Roots"]) | set(ids["Leaves"])


def test_gives_up_after_two_regenerations(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    spy = _spy(client, always_bad=True)
    r = _create(client, session_id)
    assert r.status_code == 502
    assert len(spy.counts) == 3
    with client.app.state.session_factory() as db:
        assert db.query(StudyTest).count() == 0


def test_create_is_idempotent(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    spy = _spy(client)
    first = _create(client, session_id).json()
    second = _create(client, session_id).json()
    assert first["id"] == second["id"]
    assert len(spy.counts) == 1


def test_create_requires_running_session(client: TestClient) -> None:
    session_id, _ = _setup(client, state="set_up")
    _spy(client)
    assert _create(client, session_id).status_code == 409


def test_create_unknown_session_is_404(client: TestClient) -> None:
    assert _create(client, 12345).status_code == 404


def test_resume_returns_same_question_at_current_index(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    created = _create(client, session_id).json()
    _run(client, created["id"], [0, 1])
    body = client.get(f"{API}/tests/{created['id']}").json()
    assert body["current_index"] == 2
    assert body["questions"][2]["prompt"] == created["questions"][2]["prompt"]
    assert body["questions"][2]["answer_index"] is None
    first = body["questions"][0]
    assert first["correct_index"] == 0
    assert first["explanation"]
    assert first["source"]["material"] == "Plants"


def test_resume_unknown_test_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/tests/12345").status_code == 404


def test_unanswered_questions_hide_the_answer(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    body = _create(client, session_id).json()
    for q in body["questions"]:
        assert q["correct_index"] is None
        assert q["explanation"] is None
        assert q["source"] is None


def test_answer_must_be_current_position(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    assert _answer(client, test_id, 3, 0).status_code == 409


def test_answer_unknown_position_is_404(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    assert _answer(client, test_id, 9, 0).status_code == 404


def test_repeated_answer_is_idempotent(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    assert _answer(client, test_id, 0, 0).json()["correct"] is True
    again = _answer(client, test_id, 0, 2).json()
    assert again["correct"] is True
    assert again["test"]["current_index"] == 1
    assert again["test"]["questions"][0]["answer_index"] == 0


def test_last_answer_grades_and_queues_grade(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    clock = client.app.state.clock
    clock.advance(seconds=25 * 60 + 30)
    studied = int((clock.now() - TUE).total_seconds() // 60)
    r = _run(client, test_id, [0, 0, 0, 0, 1])
    body = r.json()
    assert body["finished"] is True
    assert body["test"]["status"] == "done"
    assert body["test"]["result"] == {
        "score_pct": 80,
        "band": "B",
        "right": 4,
        "total": 5,
        "points": 80,
        "grade_queued": True,
    }
    with client.app.state.session_factory() as db:
        test = db.get(StudyTest, test_id)
        assert (test.score_pct, test.band, test.status) == (80, "B", "done")
        points = list(db.scalars(select(Points).where(Points.reason == "test")))
        assert [p.amount for p in points] == [80]
        plan = json.loads(db.get(StudySession, session_id).plan_json)
        assert next(s for s in plan["steps"] if s["key"] == "test")["status"] == "done"
    rows = _grade_rows(client)
    expected = (
        "Sam finished the daily test on Roots and 1 more: 80% (B), 4 of 5. "
        f"Studied {studied} min."
    )
    assert [r.text for r in rows] == [expected]


def test_surprise_test_doubles_points(client: TestClient) -> None:
    session_id, _ = _setup(client, exam=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    body = _run(client, test_id, [0] * 8).json()
    assert body["test"]["result"]["points"] == 200
    with client.app.state.session_factory() as db:
        assert db.scalar(select(Points.amount)) == 200


def test_all_wrong_is_f_without_points(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    body = _run(client, test_id, [1] * 5).json()
    assert body["test"]["result"]["band"] == "F"
    assert body["test"]["result"]["score_pct"] == 0
    with client.app.state.session_factory() as db:
        assert db.query(Points).count() == 0
    assert len(_grade_rows(client)) == 1


def test_no_outbox_row_before_the_last_answer(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    _run(client, test_id, [0, 0, 0, 0])
    assert _grade_rows(client) == []


def test_answer_after_done_changes_nothing(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    _run(client, test_id, [0] * 5)
    again = _answer(client, test_id, 4, 1)
    assert again.status_code == 200
    assert again.json()["finished"] is False
    assert len(_grade_rows(client)) == 1
    with client.app.state.session_factory() as db:
        assert db.query(Points).count() == 1


def test_create_after_done_returns_the_finished_test(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    spy = _spy(client)
    test_id = _create(client, session_id).json()["id"]
    _run(client, test_id, [0] * 5)
    again = _create(client, session_id).json()
    assert (again["id"], again["status"]) == (test_id, "done")
    assert len(spy.counts) == 1


def test_answer_while_session_locked_is_409(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    with client.app.state.session_factory() as db:
        db.get(StudySession, session_id).state = "locked"
        db.commit()
    assert _answer(client, test_id, 0, 0).status_code == 409
    assert client.get(f"{API}/tests/{test_id}").status_code == 200


def test_deleted_session_still_grades_without_message(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    with client.app.state.session_factory() as db:
        db.get(StudyTest, test_id).session_id = None
        db.commit()
    body = _run(client, test_id, [0] * 5).json()
    assert body["test"]["result"]["band"] == "A"
    assert body["test"]["result"]["grade_queued"] is False
    assert _grade_rows(client) == []


def test_deleted_chunk_has_no_source(client: TestClient) -> None:
    session_id, _ = _setup(client, daily=True)
    _spy(client)
    test_id = _create(client, session_id).json()["id"]
    with client.app.state.session_factory() as db:
        for q in db.scalars(select(Question)):
            q.chunk_id = None
        db.commit()
    assert _answer(client, test_id, 0, 0).json()["source"] is None
