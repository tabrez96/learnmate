import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from learnmate.models import (
    Base,
    BudgetAlert,
    Chapter,
    Chunk,
    Exam,
    Figure,
    Heartbeat,
    LlmUsage,
    Material,
    MaterialFile,
    Message,
    Outbox,
    Points,
    Question,
    SessionChapter,
    SessionEvent,
    SessionMaterial,
    StudySession,
    StudyTest,
    Subject,
)

PASSWORD = "correct horse"
KEPT = {"family", "llm_usage"}


def _setup_family(client: TestClient) -> None:
    client.put("/api/v1/family", json={"child_name": "Omar", "grade": 7})
    client.put("/api/v1/family/fallback", json={"password": PASSWORD})


def _populate(app: FastAPI) -> None:
    with app.state.session_factory() as db:

        def add(row):
            db.add(row)
            db.flush()
            return row

        subject = add(Subject(name="Science", icon="flask"))
        material = add(Material(subject_id=subject.id, title="Plants", kind="upload"))
        add(MaterialFile(material_id=material.id, path="1/page.pdf", mime="x", size=1))
        chapter = add(Chapter(material_id=material.id, name="Leaves", position=1))
        figure = add(
            Figure(
                material_id=material.id,
                chapter_id=chapter.id,
                path="1/f.png",
                description="leaf",
            )
        )
        chunk = add(
            Chunk(
                material_id=material.id,
                chapter_id=chapter.id,
                position=1,
                text="photosynthesis happens in leaves",
                figure_id=figure.id,
            )
        )
        add(Exam(subject_id=subject.id, date=dt.date(2026, 3, 1)))
        study = add(StudySession(subject_id=subject.id, type="learn", question_count=5))
        add(SessionMaterial(session_id=study.id, material_id=material.id))
        add(SessionChapter(session_id=study.id, chapter_id=chapter.id))
        add(SessionEvent(session_id=study.id, type="started"))
        add(Heartbeat(session_id=study.id))
        add(Message(session_id=study.id, role="mentor", text="hi"))
        test = add(
            StudyTest(
                session_id=study.id, subject_id=subject.id, kind="daily", graded=True
            )
        )
        add(
            Question(
                test_id=test.id,
                position=1,
                prompt="q",
                options_json="[]",
                correct_index=0,
                chunk_id=chunk.id,
            )
        )
        add(Points(session_id=study.id, reason="test", amount=5))
        add(Outbox(text="alert"))
        add(LlmUsage(model="m", purpose="lesson", cost_usd=0.01, input_tokens=1))
        add(BudgetAlert(month="2026-03", level=80))
        db.commit()
    page = app.state.settings.data_dir / "files" / "1" / "page.pdf"
    page.parent.mkdir(parents=True)
    page.write_bytes(b"pdf")


def _counts(app: FastAPI) -> dict[str, int]:
    with app.state.session_factory() as db:
        return {
            t.name: db.scalar(select(func.count()).select_from(t))
            for t in Base.metadata.sorted_tables
        }


def _delete(client: TestClient, password: str):
    return client.request("DELETE", "/api/v1/data", json={"password": password})


def test_delete_keeps_family_and_llm_usage_and_removes_everything_else(
    client: TestClient, app: FastAPI
) -> None:
    _setup_family(client)
    _populate(app)
    before = _counts(app)
    assert all(n >= 1 for n in before.values()), before

    assert _delete(client, PASSWORD).status_code == 204

    after = _counts(app)
    for name, n in after.items():
        assert n == (before[name] if name in KEPT else 0), name
    with app.state.session_factory() as db:
        hits = db.scalar(
            text(
                "SELECT count(*) FROM chunk_fts WHERE chunk_fts MATCH 'photosynthesis'"
            )
        )
    assert hits == 0
    files = app.state.settings.data_dir / "files"
    assert files.is_dir()
    assert list(files.iterdir()) == []
    assert (app.state.settings.data_dir / "learnmate.db").exists()


def test_delete_with_wrong_password_is_403_and_keeps_data(
    client: TestClient, app: FastAPI
) -> None:
    _setup_family(client)
    _populate(app)
    before = _counts(app)
    assert _delete(client, "wrong password").status_code == 403
    assert _counts(app) == before
    assert (app.state.settings.data_dir / "files" / "1" / "page.pdf").exists()


def test_delete_without_fallback_set_is_403(client: TestClient) -> None:
    client.put("/api/v1/family", json={"child_name": "Omar", "grade": 7})
    assert _delete(client, "anything").status_code == 403


def test_delete_before_family_exists_is_403(client: TestClient) -> None:
    assert _delete(client, "anything").status_code == 403


def test_delete_reports_file_removal_failure(
    client: TestClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_family(client)
    _populate(app)

    def fail(path):
        raise PermissionError("cannot remove")

    monkeypatch.setattr("learnmate.api.data.shutil.rmtree", fail)
    with pytest.raises(PermissionError):
        _delete(client, PASSWORD)
    assert (app.state.settings.data_dir / "files" / "1" / "page.pdf").exists()


def test_delete_creates_files_dir_when_missing(
    client: TestClient, app: FastAPI
) -> None:
    _setup_family(client)
    assert not (app.state.settings.data_dir / "files").exists()
    assert _delete(client, PASSWORD).status_code == 204
    assert (app.state.settings.data_dir / "files").is_dir()
