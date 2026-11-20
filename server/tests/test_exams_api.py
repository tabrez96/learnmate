import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from learnmate.clock import FakeClock
from learnmate.models import Subject

API = "/api/v1"


@pytest.fixture(autouse=True)
def _fixed_clock(client: TestClient) -> None:
    client.app.state.clock = FakeClock()


def _subject(client: TestClient, name: str = "Science") -> int:
    with client.app.state.session_factory() as db:
        subject = Subject(name=name, icon="flask")
        db.add(subject)
        db.commit()
        return subject.id


def test_add_list_edit_delete_exam(client: TestClient) -> None:
    subject_id = _subject(client)
    created = client.post(
        f"{API}/exams", json={"subject_id": subject_id, "date": "2026-02-01"}
    )
    assert created.status_code == 201
    exam = created.json()
    assert exam["subject_name"] == "Science"
    assert client.get(f"{API}/exams").json() == [exam]
    edited = client.patch(f"{API}/exams/{exam['id']}", json={"date": "2026-02-03"})
    assert edited.status_code == 200
    assert edited.json()["date"] == "2026-02-03"
    assert client.delete(f"{API}/exams/{exam['id']}").status_code == 204
    assert client.get(f"{API}/exams").json() == []


def test_exam_filters_by_subject(client: TestClient) -> None:
    science, maths = _subject(client), _subject(client, "Maths")
    for subject_id, date in ((science, "2026-02-02"), (maths, "2026-02-01")):
        client.post(f"{API}/exams", json={"subject_id": subject_id, "date": date})
    everything = client.get(f"{API}/exams").json()
    assert [e["subject_name"] for e in everything] == ["Maths", "Science"]
    only = client.get(f"{API}/exams", params={"subject_id": science}).json()
    assert [e["subject_name"] for e in only] == ["Science"]


def test_exam_duplicate_rejected(client: TestClient) -> None:
    subject_id = _subject(client)
    body = {"subject_id": subject_id, "date": "2026-02-01"}
    assert client.post(f"{API}/exams", json=body).status_code == 201
    assert client.post(f"{API}/exams", json=body).status_code == 409
    other = client.post(f"{API}/exams", json={**body, "date": "2026-02-02"}).json()
    clash = client.patch(f"{API}/exams/{other['id']}", json={"date": "2026-02-01"})
    assert clash.status_code == 409
    same = client.patch(f"{API}/exams/{other['id']}", json={"date": "2026-02-02"})
    assert same.status_code == 200


def test_exam_unknown_subject(client: TestClient) -> None:
    r = client.post(f"{API}/exams", json={"subject_id": 999, "date": "2026-02-01"})
    assert r.status_code == 422


def test_exam_in_past(client: TestClient) -> None:
    subject_id = _subject(client)
    past = client.post(
        f"{API}/exams", json={"subject_id": subject_id, "date": "2026-01-04"}
    )
    assert past.status_code == 422
    today = client.post(
        f"{API}/exams", json={"subject_id": subject_id, "date": "2026-01-05"}
    )
    assert today.status_code == 201


def test_exam_not_found(client: TestClient) -> None:
    assert (
        client.patch(f"{API}/exams/9", json={"date": "2026-02-01"}).status_code == 404
    )
    assert client.delete(f"{API}/exams/9").status_code == 404


def test_exams_require_device_token(app: FastAPI) -> None:
    with TestClient(app) as bare:
        assert bare.get(f"{API}/exams").status_code == 401
        assert bare.get(f"{API}/progress").status_code == 401
        assert bare.get(f"{API}/sessions/1/plan").status_code == 401
