import logging
import sqlite3
import tempfile
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from learnmate import ingest
from learnmate.classroom import InvalidLink, parse_link
from learnmate.models import Chunk, Material
from tests.fake_google import TOKEN, FakeGoogle

PDF = b"%PDF-1.4\nhello"
EXPORT = b"%PDF-1.4\nexported doc"
LINK = "https://classroom.google.com/c/MTEx/a/MjIy/details"
KEY = ("111", "courseWork", "222")
DOC = "application/vnd.google-apps.document"
FIXTURE = Path(__file__).parent / "ingest" / "fixtures" / "typed.pdf"


@pytest.fixture
def google(app) -> FakeGoogle:
    fake = FakeGoogle()
    app.state.google_transport = fake.transport
    return fake


@pytest.fixture
def subject_id(client) -> int:
    return client.post("/api/v1/subjects", json={"name": "Science"}).json()["id"]


def _drive(google, drive_id, mime="application/pdf", content=PDF, **meta):
    google.files[drive_id] = (
        {"id": drive_id, "name": f"{drive_id}.x", "mimeType": mime, **meta},
        content,
    )
    return {"driveFile": {"driveFile": {"id": drive_id}}}


def _post(google, *materials, title="Light and shadows"):
    google.posts[KEY] = {"title": title, "materials": list(materials)}


def _import(client, subject_id, link=LINK, token=TOKEN, **extra):
    return client.post(
        f"/api/v1/subjects/{subject_id}/materials/classroom",
        json={"link": link, "access_token": token, **extra},
    )


def _material_count(app) -> int:
    with app.state.session_factory() as db:
        return db.scalar(select(func.count()).select_from(Material))


def _stored(settings) -> list:
    root = settings.data_dir / "files"
    return list(root.rglob("*")) if root.exists() else []


def test_parse_link_assignment_and_material():
    a = parse_link(LINK)
    assert (a.kind, a.course_id, a.item_id) == ("courseWork", "111", "222")
    m = parse_link("https://classroom.google.com/u/1/c/MTEx/m/MjIy/details?cjc=x#f")
    assert m.kind == "courseWorkMaterials"
    assert m.url == "https://classroom.google.com/c/MTEx/m/MjIy/details"
    n = parse_link("https://classroom.google.com/c/111/a/222")
    assert (n.course_id, n.item_id) == ("111", "222")


@pytest.mark.parametrize(
    "text",
    [
        "https://drive.google.com/file/d/abc/view",
        "http://classroom.google.com/c/MTEx/a/MjIy",
        "https://classroom.google.com/c/MTEx",
        "https://evil.example/c/MTEx/a/MjIy",
        "hello",
        "",
    ],
)
def test_parse_link_rejects_other_links(text):
    with pytest.raises(InvalidLink):
        parse_link(text)


def test_classroom_downloads_attachments(
    client, app, settings, google, subject_id, monkeypatch
):
    calls = []
    monkeypatch.setattr(ingest, "ingest", lambda *a, **kw: calls.append(a))
    _post(
        google,
        _drive(google, "d1"),
        _drive(google, "d2", mime=DOC, content=b""),
        {"youtubeVideo": {"id": "x"}},
    )
    google.exports["d2"] = EXPORT
    r = _import(client, subject_id, chapters=" Ch 3 ")
    assert r.status_code == 201
    body = r.json()
    assert body["kind"] == "classroom"
    assert body["title"] == "Light and shadows"
    assert body["chapters_hint"] == "Ch 3"
    assert body["file_types"] == ["application/pdf", "application/pdf"]
    folder = settings.data_dir / "files" / str(body["id"])
    assert (folder / "01.pdf").read_bytes() == PDF
    assert (folder / "02.pdf").read_bytes() == EXPORT
    with app.state.session_factory() as db:
        assert db.get(Material, body["id"]).source_url == LINK
    export = [r for r in google.requests if r.url.path.endswith("/export")]
    assert export[0].url.params["mimeType"] == "application/pdf"
    assert calls and calls[0][2] == body["id"]


def test_classroom_title_from_request_wins(client, google, subject_id, monkeypatch):
    monkeypatch.setattr(ingest, "ingest", lambda *a, **kw: None)
    _post(google, _drive(google, "d1"), title="")
    assert _import(client, subject_id).json()["title"] == "Classroom material"
    assert _import(client, subject_id, title="Mine").json()["title"] == "Mine"


def test_classroom_material_is_ingested(client, app, google, subject_id):
    _post(google, _drive(google, "d1", content=FIXTURE.read_bytes()))
    r = _import(client, subject_id)
    assert r.status_code == 201
    material_id = r.json()["id"]
    assert client.get(f"/api/v1/materials/{material_id}").json()["status"] == "ready"
    with app.state.session_factory() as db:
        count = db.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.material_id == material_id)
        )
    assert count >= 1


def test_unsupported_attachments_are_skipped(
    client, settings, google, subject_id, monkeypatch
):
    monkeypatch.setattr(ingest, "ingest", lambda *a, **kw: None)
    pptx = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    _post(google, _drive(google, "d1"), _drive(google, "d2", mime=pptx))
    r = _import(client, subject_id)
    assert r.status_code == 201
    assert r.json()["file_types"] == ["application/pdf"]
    assert len(_stored(settings)) == 2  # the folder and one file


def test_mismatched_content_is_skipped(client, google, subject_id, monkeypatch):
    monkeypatch.setattr(ingest, "ingest", lambda *a, **kw: None)
    _post(google, _drive(google, "d1"), _drive(google, "d2", content=b"not a pdf"))
    assert _import(client, subject_id).json()["file_types"] == ["application/pdf"]


def test_no_usable_attachments(client, app, settings, google, subject_id):
    _post(google, {"youtubeVideo": {"id": "x"}})
    r = _import(client, subject_id)
    assert r.status_code == 422
    assert r.json()["error"] == "classroom_no_files"
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_too_many_files(client, app, settings, google, subject_id):
    settings.upload_max_files = 1
    _post(google, _drive(google, "d1"), _drive(google, "d2"))
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (422, "classroom_too_many_files")
    assert _material_count(app) == 0


def test_access_denied_on_classroom(client, app, settings, google, subject_id):
    _post(google, _drive(google, "d1"))
    google.fail["/v1/courses/"] = 403
    r = _import(client, subject_id)
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "classroom_access_denied"
    assert body["detail"]
    assert _material_count(app) == 0
    assert _stored(settings) == []


@pytest.mark.parametrize("status", [403, 404])
def test_access_denied_on_drive(client, app, settings, google, subject_id, status):
    _post(google, _drive(google, "d1"))
    google.fail["/drive/v3/files/"] = status
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (403, "classroom_access_denied")
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_error_part_way_stores_nothing(client, app, settings, google, subject_id):
    _post(google, _drive(google, "d1"), _drive(google, "d2"))
    google.fail["/drive/v3/files/d2"] = 403
    assert _import(client, subject_id).status_code == 403
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_error_after_a_finished_download_closes_it(
    client, app, settings, google, subject_id, monkeypatch
):
    opened = []
    real = tempfile.TemporaryFile

    def recording(*args, **kwargs):
        f = real(*args, **kwargs)
        opened.append(f)
        return f

    monkeypatch.setattr("learnmate.classroom.google.tempfile.TemporaryFile", recording)
    _post(google, _drive(google, "d1"), _drive(google, "d2", mime=DOC, content=b""))
    google.exports["d2"] = EXPORT
    google.fail["/drive/v3/files/d2/export"] = 403
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (403, "classroom_access_denied")
    assert len(opened) == 2
    assert all(f.closed for f in opened)
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_expired_token_asks_to_sign_in_again(client, google, subject_id):
    _post(google, _drive(google, "d1"))
    r = _import(client, subject_id, token="ya29.other")
    assert (r.status_code, r.json()["error"]) == (409, "classroom_sign_in_again")


def test_post_not_found(client, google, subject_id):
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (404, "classroom_not_found")


@pytest.mark.parametrize("forced", [500, 429, httpx.ConnectError("down")])
def test_google_unavailable(client, google, subject_id, forced):
    _post(google, _drive(google, "d1"))
    google.fail["/v1/courses/"] = forced
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (502, "classroom_unavailable")


def test_download_error_is_unavailable(client, google, subject_id):
    _post(google, _drive(google, "d1"))
    google.fail["/drive/v3/files/d1"] = httpx.ReadTimeout("slow")
    assert _import(client, subject_id).json()["error"] == "classroom_unavailable"


def test_file_too_large(client, app, settings, google, subject_id):
    settings.upload_max_mb = 1
    big = 2 * 1024 * 1024
    _post(google, _drive(google, "d1", size=str(big)))
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (413, "classroom_file_too_large")

    _post(google, _drive(google, "d2", mime=DOC, content=b""))
    google.exports["d2"] = b"%PDF" + b"0" * big
    r = _import(client, subject_id)
    assert (r.status_code, r.json()["error"]) == (413, "classroom_file_too_large")
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_invalid_link_makes_no_google_call(client, google, subject_id):
    r = _import(client, subject_id, link="https://classroom.google.com/c/MTEx")
    assert (r.status_code, r.json()["error"]) == (422, "classroom_link_invalid")
    assert google.requests == []


def test_blank_token_is_rejected(client, google, subject_id):
    assert _import(client, subject_id, token="  ").status_code == 422
    assert google.requests == []


def test_unknown_subject(client, google):
    r = _import(client, 999)
    assert r.status_code == 404
    assert google.requests == []


def test_google_requests_carry_bearer_token(client, google, subject_id, monkeypatch):
    monkeypatch.setattr(ingest, "ingest", lambda *a, **kw: None)
    _post(google, _drive(google, "d1"))
    assert _import(client, subject_id).status_code == 201
    assert google.requests
    for request in google.requests:
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert TOKEN not in str(request.url)


def test_token_never_stored_or_logged(client, settings, google, subject_id, caplog):
    caplog.set_level(logging.DEBUG)
    _post(google, _drive(google, "d1", content=FIXTURE.read_bytes()))
    ok = _import(client, subject_id)
    google.fail["/v1/courses/"] = 403
    denied = _import(client, subject_id)
    assert (ok.status_code, denied.status_code) == (201, 403)
    assert TOKEN not in caplog.text
    assert TOKEN not in ok.text + denied.text
    dump = "\n".join(sqlite3.connect(settings.data_dir / "learnmate.db").iterdump())
    assert TOKEN not in dump
    for path in settings.data_dir.rglob("*"):
        if path.is_file():
            assert TOKEN.encode() not in path.read_bytes()
