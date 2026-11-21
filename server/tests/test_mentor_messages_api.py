import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from learnmate.api.family import FAMILY_ID
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import BooksAnswer
from learnmate.mentor import chat
from learnmate.models import Chunk, Family, Figure, Material, Message, Subject
from learnmate.rag.search import SearchHit
from tests.test_mentor_api import API, BAD, _exhaust_budget, _setup

VISUAL = {
    "kind": "chart",
    "chart_type": "bar",
    "caption": "Root length",
    "alt_text": "Bars of root length by week",
    "labels": ["w1", "w2"],
    "values": [1, 2],
}


class Scripted(FakeLlm):
    def __init__(self, settings, *replies: BooksAnswer) -> None:
        super().__init__(settings)
        self.replies = list(replies)

    def answer_from_passages(self, question, *, history, passages, grade):
        result = super().answer_from_passages(
            question, history=history, passages=passages, grade=grade
        )
        if self.replies:
            return type(result)(self.replies.pop(0), result.usage)
        return result


def _url(session_id: int) -> str:
    return f"{API}/sessions/{session_id}/mentor/messages"


def _hits(client: TestClient, ids: list[int]) -> list[SearchHit]:
    with client.app.state.session_factory() as db:
        chunks = db.scalars(select(Chunk).where(Chunk.id.in_(ids)).order_by(Chunk.id))
        return [
            SearchHit(
                id=c.id,
                chunk_ids=[c.id],
                material_id=c.material_id,
                chapter_id=c.chapter_id,
                page=c.page,
                text=c.text,
                score=0.9 - i / 10,
            )
            for i, c in enumerate(chunks)
        ]


def _prepare(client, monkeypatch, *replies, state="running", found=True):
    session_id, ids = _setup(client, state=state)
    hits = _hits(client, ids["Roots"]) if found else []
    monkeypatch.setattr(chat, "search", lambda *a, **k: hits)
    llm = Scripted(client.app.state.settings, *replies)
    client.app.state.llm.inner = llm
    return session_id, ids, llm


def _ok(ids: list[int], **kw) -> BooksAnswer:
    return BooksAnswer(covered=True, text="Roots drink.", passage_ids=ids, **kw)


def _family(client: TestClient, **fields) -> None:
    with client.app.state.session_factory() as db:
        for k, v in fields.items():
            setattr(db.get(Family, FAMILY_ID), k, v)
        db.commit()


def _rows(client: TestClient) -> list[Message]:
    with client.app.state.session_factory() as db:
        return list(db.scalars(select(Message).order_by(Message.id)))


def test_post_books_answer_with_sources_and_visual(client, monkeypatch) -> None:
    session_id, ids, _ = _prepare(client, monkeypatch)
    llm = client.app.state.llm.inner
    llm.replies = [_ok([ids["Roots"][1]], visual=VISUAL)]
    r = client.post(_url(session_id), json={"text": "What do roots do?"})
    assert r.status_code == 200
    body = r.json()
    assert body["question"]["role"] == "student"
    answer = body["answer"]
    source = answer["sources"][0]
    assert source["material"] == "Plants"
    assert source["chapter"] == "Roots"
    assert source["page"] == 2
    assert answer["visual"]["chart_type"] == "bar"
    assert answer["can_check_outside"] is False
    assert [m.role for m in _rows(client)] == ["student", "mentor"]


def test_post_books_cites_outside_retrieved_set_retried_then_not_covered(
    client, monkeypatch
) -> None:
    bad = _ok([BAD])
    session_id, _, llm = _prepare(client, monkeypatch, bad, bad)
    r = client.post(_url(session_id), json={"text": "q"})
    answer = r.json()["answer"]
    assert answer["text"] == "Your books don't cover this."
    assert answer["can_check_outside"] is True
    assert answer["sources"] == []
    assert llm.calls.count("answer") == 2


def test_post_below_floor_no_model_call(client, monkeypatch) -> None:
    session_id, _, llm = _prepare(client, monkeypatch, found=False)
    r = client.post(_url(session_id), json={"text": "q"})
    assert r.json()["answer"]["can_check_outside"] is True
    assert "answer" not in llm.calls
    record = json.loads(_rows(client)[1].retrieval_json)
    assert record["hits"] == []


def test_no_outside_offer_when_setting_off(client, monkeypatch) -> None:
    session_id, _, _ = _prepare(client, monkeypatch, found=False)
    _family(client, outside_books_allowed=False)
    r = client.post(_url(session_id), json={"text": "q"})
    assert r.json()["answer"]["can_check_outside"] is False


def test_post_outside_refused_when_setting_off(client, monkeypatch) -> None:
    session_id, _, llm = _prepare(client, monkeypatch)
    _family(client, outside_books_allowed=False)
    r = client.post(_url(session_id), json={"text": "q", "mode": "outside"})
    assert r.status_code == 403
    assert "outside" not in llm.calls
    assert _rows(client) == []


def test_post_outside_stored_with_url(client, monkeypatch) -> None:
    session_id, _, _ = _prepare(client, monkeypatch)
    r = client.post(_url(session_id), json={"text": "q", "mode": "outside"})
    answer = r.json()["answer"]
    assert r.status_code == 200
    assert answer["outside"] is True
    assert answer["source_url"] == "https://example.org/source"
    assert answer["can_check_outside"] is False
    assert _rows(client)[1].outside is True


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "https://", "http:///path", "https://:80/x"]
)
def test_post_outside_bad_url_is_502(client, monkeypatch, url: str) -> None:
    session_id, _, llm = _prepare(client, monkeypatch)

    def no_url(question, *, history, grade):
        result = FakeLlm.answer_outside(llm, question, history=history, grade=grade)
        result.value.source_url = url
        return result

    monkeypatch.setattr(llm, "answer_outside", no_url)
    r = client.post(_url(session_id), json={"text": "q", "mode": "outside"})
    assert r.status_code == 502
    assert _rows(client) == []


def test_every_mentor_message_stores_retrieval(client, monkeypatch) -> None:
    session_id, ids, llm = _prepare(client, monkeypatch)
    llm.replies = [_ok([ids["Roots"][0]]), _ok([BAD]), _ok([BAD])]
    for body in (
        {"text": "one"},
        {"text": "two"},
        {"text": "three", "mode": "outside"},
    ):
        assert client.post(_url(session_id), json=body).status_code == 200
    mentor = [m for m in _rows(client) if m.role == "mentor"]
    assert len(mentor) == 3
    for m in mentor:
        record = json.loads(m.retrieval_json)
        assert "query" in record
        assert record["rerank"] is False
    books = json.loads(mentor[0].retrieval_json)
    assert set(books["hits"][0]) == {"passage_id", "chunk_ids", "score"}
    assert json.loads(mentor[1].retrieval_json)["covered"] is False
    assert json.loads(mentor[2].retrieval_json)["query"] == "three"


def test_post_requires_running_session(client, monkeypatch) -> None:
    session_id, _, _ = _prepare(client, monkeypatch, state="set_up")
    assert client.post(_url(session_id), json={"text": "q"}).status_code == 409
    assert client.post(_url(99999), json={"text": "q"}).status_code == 404
    assert client.get(_url(99999)).status_code == 404


def test_post_validates_text(client, monkeypatch) -> None:
    session_id, _, _ = _prepare(client, monkeypatch)
    for text in ("   ", "x" * 2001):
        assert client.post(_url(session_id), json={"text": text}).status_code == 422


def test_post_stops_when_budget_is_spent(client, monkeypatch) -> None:
    session_id, _, llm = _prepare(client, monkeypatch)
    _exhaust_budget(client)
    r = client.post(_url(session_id), json={"text": "q"})
    assert r.status_code >= 400
    assert llm.calls == []


def test_follow_up_uses_history(client, monkeypatch) -> None:
    session_id, _, llm = _prepare(client, monkeypatch)
    client.post(_url(session_id), json={"text": "one"})
    client.post(_url(session_id), json={"text": "and then?"})
    assert llm.calls.count("rewrite") == 1


def test_get_messages_in_order(client, monkeypatch) -> None:
    session_id, _, _ = _prepare(client, monkeypatch)
    for text in ("one", "two"):
        client.post(_url(session_id), json={"text": text})
    got = client.get(_url(session_id)).json()
    assert [m["role"] for m in got] == ["student", "mentor"] * 2
    assert [m["text"] for m in got][::2] == ["one", "two"]
    assert [m["id"] for m in got] == sorted(m["id"] for m in got)


def test_get_works_when_session_not_running(client, monkeypatch) -> None:
    session_id, _, _ = _prepare(client, monkeypatch, state="set_up")
    assert client.get(_url(session_id)).json() == []


def _figure_visual(figure_id: int) -> dict:
    return {
        "kind": "figure",
        "figure_id": figure_id,
        "caption": "Root",
        "alt_text": "A drawing of a root",
    }


def _add_figure(client: TestClient, chunk_id: int | None, *, other: bool) -> int:
    with client.app.state.session_factory() as db:
        if other:
            subject = Subject(name="Maths", icon="calc")
            db.add(subject)
            db.flush()
            material = Material(subject_id=subject.id, title="Sums", kind="upload")
            db.add(material)
            db.flush()
            material_id, chapter_id = material.id, None
        else:
            chunk = db.get(Chunk, chunk_id)
            material_id, chapter_id = chunk.material_id, chunk.chapter_id
        figure = Figure(
            material_id=material_id,
            chapter_id=chapter_id,
            page=1,
            path=f"{material_id}/fig-001-1.png",
            description="A root",
        )
        db.add(figure)
        db.commit()
        return figure.id


def test_books_answer_with_scope_figure_keeps_visual(client, monkeypatch) -> None:
    session_id, ids, llm = _prepare(client, monkeypatch)
    figure_id = _add_figure(client, ids["Roots"][0], other=False)
    llm.replies = [_ok([ids["Roots"][1]], visual=_figure_visual(figure_id))]
    r = client.post(_url(session_id), json={"text": "Show a root"})
    visual = r.json()["answer"]["visual"]
    assert (visual["kind"], visual["figure_id"]) == ("figure", figure_id)


def test_books_answer_with_figure_outside_scope_has_no_visual(
    client, monkeypatch
) -> None:
    session_id, ids, llm = _prepare(client, monkeypatch)
    figure_id = _add_figure(client, None, other=True)
    reply = _ok([ids["Roots"][1]], visual=_figure_visual(figure_id))
    llm.replies = [reply, reply]
    r = client.post(_url(session_id), json={"text": "Show a root"})
    answer = r.json()["answer"]
    assert answer["text"] == "Roots drink."
    assert answer["visual"] is None
