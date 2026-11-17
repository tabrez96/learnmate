import datetime as dt
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from learnmate.config import Settings
from learnmate.models import (
    Chapter,
    Chunk,
    Exam,
    Figure,
    Material,
    MaterialFile,
    Question,
    SessionMaterial,
    StudySession,
    StudyTest,
    Subject,
)

PDF = b"%PDF-1.4\nhello"


def _subject(client: TestClient, name: str = "Science") -> dict:
    return client.post("/api/v1/subjects", json={"name": name}).json()


def _count(app: FastAPI, model) -> int:
    with app.state.session_factory() as db:
        return db.scalar(select(func.count()).select_from(model))


def _add_test(app, subject_id, *, status, score, band, day, graded=True):
    with app.state.session_factory() as db:
        db.add(
            StudyTest(
                subject_id=subject_id,
                kind="daily",
                status=status,
                graded=graded,
                score_pct=score,
                band=band,
                created_at=dt.datetime(2026, 1, day),
                finished_at=dt.datetime(2026, 1, day, 10),
            )
        )
        db.commit()


def test_create_subject_picks_icon_from_name(client):
    r = client.post("/api/v1/subjects", json={"name": "Maths"})
    assert r.status_code == 201
    body = r.json()
    assert body["icon"] == "calculator"
    assert body["material_count"] == 0
    assert body["latest_grade"] is None
    assert body["average_pct"] is None


def test_create_subject_unknown_name_gets_book_icon(client):
    assert _subject(client, "Art")["icon"] == "book"


def test_create_subject_keeps_given_icon(client):
    r = client.post("/api/v1/subjects", json={"name": "Maths", "icon": "atom"})
    assert r.json()["icon"] == "atom"


def test_duplicate_subject_name_is_409_case_insensitive(client):
    _subject(client, "Science")
    assert client.post("/api/v1/subjects", json={"name": "science"}).status_code == 409
    other = _subject(client, "Art")
    r = client.patch(f"/api/v1/subjects/{other['id']}", json={"name": "SCIENCE"})
    assert r.status_code == 409


def test_duplicate_subject_name_is_409_for_non_ascii_names(client):
    _subject(client, "Économie")
    assert client.post("/api/v1/subjects", json={"name": "Économie"}).status_code == 409
    assert client.post("/api/v1/subjects", json={"name": "économie"}).status_code == 409


def test_blank_subject_name_is_422(client):
    assert client.post("/api/v1/subjects", json={"name": "   "}).status_code == 422


def test_list_subjects_has_material_count_latest_grade_and_average(client, app):
    science = _subject(client, "Science")
    other = _subject(client, "Art")
    client.post(
        f"/api/v1/subjects/{science['id']}/materials",
        files={"files": ("a.pdf", PDF, "application/pdf")},
    )
    _add_test(app, science["id"], status="done", score=60, band="D", day=1)
    _add_test(app, science["id"], status="done", score=90, band="A", day=2)
    _add_test(app, science["id"], status="missed", score=None, band=None, day=3)

    rows = {s["name"]: s for s in client.get("/api/v1/subjects").json()}
    assert rows["Science"]["material_count"] == 1
    assert rows["Science"]["latest_grade"]["status"] == "missed"
    assert rows["Science"]["latest_grade"]["score_pct"] is None
    assert rows["Science"]["latest_grade"]["band"] is None
    assert rows["Science"]["average_pct"] == 75
    assert rows["Art"]["material_count"] == 0
    assert rows["Art"]["latest_grade"] is None
    assert rows["Art"]["average_pct"] is None
    assert other["id"] != science["id"]


def test_latest_grade_shows_score_and_band_for_done_test(client, app):
    s = _subject(client)
    _add_test(app, s["id"], status="done", score=85, band="B", day=1)
    grade = client.get("/api/v1/subjects").json()[0]["latest_grade"]
    assert (grade["status"], grade["score_pct"], grade["band"]) == ("done", 85, "B")


def test_ungraded_tests_do_not_count_as_grades(client, app):
    s = _subject(client)
    _add_test(app, s["id"], status="done", score=100, band="A", day=1, graded=False)
    row = client.get("/api/v1/subjects").json()[0]
    assert row["latest_grade"] is None
    assert row["average_pct"] is None


def test_patch_subject_renames_and_changes_icon(client):
    s = _subject(client, "Art")
    r = client.patch(
        f"/api/v1/subjects/{s['id']}", json={"name": " Drawing ", "icon": "leaf"}
    )
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["icon"]) == ("Drawing", "leaf")


def test_patch_with_empty_body_and_same_name_is_unchanged(client):
    s = _subject(client, "Art")
    assert client.patch(f"/api/v1/subjects/{s['id']}", json={}).json() == s
    r = client.patch(f"/api/v1/subjects/{s['id']}", json={"name": "art"})
    assert r.status_code == 200


def test_patch_missing_subject_is_404(client):
    assert client.patch("/api/v1/subjects/99", json={"name": "x"}).status_code == 404


def test_delete_missing_subject_is_404(client):
    assert client.delete("/api/v1/subjects/99").status_code == 404


def test_delete_subject_removes_material_files_chapters_chunks_figures_keeps_tests_and_grades(
    client, app, settings: Settings
):
    subject = _subject(client)
    material = client.post(
        f"/api/v1/subjects/{subject['id']}/materials",
        files={"files": ("a.pdf", PDF, "application/pdf")},
    ).json()
    mid = material["id"]
    assert (settings.data_dir / "files" / str(mid)).is_dir()
    with app.state.session_factory() as db:
        chapter = Chapter(material_id=mid, name="Leaves", position=1)
        db.add(chapter)
        db.flush()
        figure = Figure(
            material_id=mid, chapter_id=chapter.id, path=f"{mid}/f.png", description="x"
        )
        db.add(figure)
        db.flush()
        chunk = Chunk(
            material_id=mid,
            chapter_id=chapter.id,
            position=1,
            text="photosynthesis",
            figure_id=figure.id,
        )
        db.add(chunk)
        db.add(Exam(subject_id=subject["id"], date=dt.date(2026, 3, 1)))
        session = StudySession(subject_id=subject["id"], type="learn", question_count=1)
        db.add(session)
        db.flush()
        db.add(SessionMaterial(session_id=session.id, material_id=mid))
        test = StudyTest(
            subject_id=subject["id"],
            session_id=session.id,
            kind="daily",
            status="done",
            graded=True,
            score_pct=80,
            band="B",
        )
        db.add(test)
        db.flush()
        db.add(
            Question(
                test_id=test.id,
                position=1,
                prompt="p",
                options_json="[]",
                correct_index=0,
                chunk_id=chunk.id,
            )
        )
        db.commit()

    assert client.delete(f"/api/v1/subjects/{subject['id']}").status_code == 204

    for model in (
        Material,
        MaterialFile,
        Chapter,
        Figure,
        Chunk,
        Exam,
        SessionMaterial,
    ):
        assert _count(app, model) == 0, model
    with app.state.session_factory() as db:
        hits = db.scalar(
            text(
                "SELECT count(*) FROM chunk_fts WHERE chunk_fts MATCH 'photosynthesis'"
            )
        )
        assert hits == 0
        test = db.scalars(select(StudyTest)).one()
        assert (test.score_pct, test.band, test.subject_id) == (80, "B", None)
        assert db.scalars(select(StudySession)).one() is not None
        assert db.scalars(select(Question)).one().chunk_id is None
        assert db.get(Subject, subject["id"]) is None
    assert not (settings.data_dir / "files" / str(mid)).exists()


def test_delete_subject_leaves_other_subjects_material(client, app, settings: Settings):
    a, b = _subject(client, "Science"), _subject(client, "Art")
    ids = []
    for s in (a, b):
        r = client.post(
            f"/api/v1/subjects/{s['id']}/materials",
            files={"files": ("a.pdf", PDF, "application/pdf")},
        )
        ids.append(r.json()["id"])
    assert client.delete(f"/api/v1/subjects/{a['id']}").status_code == 204
    assert _count(app, Material) == 1
    assert not (settings.data_dir / "files" / str(ids[0])).exists()
    assert (settings.data_dir / "files" / str(ids[1]) / "01.pdf").exists()


def test_delete_subject_when_files_already_gone_is_204(client, settings: Settings):
    s = _subject(client)
    mid = client.post(
        f"/api/v1/subjects/{s['id']}/materials",
        files={"files": ("a.pdf", PDF, "application/pdf")},
    ).json()["id"]
    import shutil

    shutil.rmtree(Path(settings.data_dir) / "files" / str(mid))
    assert client.delete(f"/api/v1/subjects/{s['id']}").status_code == 204


def test_delete_subject_without_material_is_204(client):
    s = _subject(client)
    assert client.delete(f"/api/v1/subjects/{s['id']}").status_code == 204
