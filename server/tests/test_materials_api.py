import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from learnmate import ingest
from learnmate.config import Settings
from learnmate.files import UnsupportedFile, resolve_stored, sniff
from learnmate.models import Chapter, Chunk, Figure, Material, MaterialFile, Subject

PDF = b"%PDF-1.4\nhello"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 8
DOCX = b"PK\x03\x04" + b"0" * 12


@pytest.fixture
def subject_id(client: TestClient) -> int:
    return client.post("/api/v1/subjects", json={"name": "Science"}).json()["id"]


def _upload(client, subject_id, files, **data):
    return client.post(
        f"/api/v1/subjects/{subject_id}/materials", files=files, data=data
    )


def _pdf(name="a.pdf", body=PDF):
    return ("files", (name, body, "application/octet-stream"))


def _material_count(app) -> int:
    with app.state.session_factory() as db:
        return db.scalar(select(func.count()).select_from(Material))


def _stored(settings: Settings) -> list:
    root = settings.data_dir / "files"
    return list(root.rglob("*")) if root.exists() else []


def test_upload_creates_reading_material_and_stores_files(
    client, app, settings, subject_id
):
    r = _upload(
        client,
        subject_id,
        [_pdf("one.pdf"), ("files", ("two.png", PNG, "image/png"))],
        chapters="Ch 3 Light",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "reading"
    assert body["pages_read"] == 0
    assert body["chapters_hint"] == "Ch 3 Light"
    assert body["file_types"] == ["application/pdf", "image/png"]
    folder = settings.data_dir / "files" / str(body["id"])
    assert (folder / "01.pdf").read_bytes() == PDF
    assert (folder / "02.png").read_bytes() == PNG
    with app.state.session_factory() as db:
        paths = list(db.scalars(select(MaterialFile.path).order_by(MaterialFile.id)))
    assert paths == [f"{body['id']}/01.pdf", f"{body['id']}/02.png"]


def test_upload_accepts_word_file(client, subject_id):
    r = _upload(client, subject_id, [_pdf("notes.DOCX", DOCX)])
    assert r.status_code == 201


def test_upload_title_defaults_to_first_file_name(client, subject_id):
    r = _upload(client, subject_id, [_pdf("Plants.pdf")])
    assert r.json()["title"] == "Plants"
    r = _upload(client, subject_id, [_pdf("Plants.pdf")], title="  My notes ")
    assert r.json()["title"] == "My notes"


def test_upload_filename_never_used_on_disk(client, settings, subject_id):
    r = _upload(client, subject_id, [_pdf("../../etc/x.pdf")])
    assert r.status_code == 201
    names = {p.name for p in _stored(settings)}
    assert "x.pdf" not in names
    assert "01.pdf" in names


def test_upload_starts_ingest_in_background(
    client, subject_id, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        ingest,
        "ingest",
        lambda factory, settings, mid, **kwargs: calls.append(mid),
    )
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    assert calls == [mid]


def test_upload_rejects_unsupported_type_with_clear_error(
    client, app, settings, subject_id
):
    r = _upload(client, subject_id, [_pdf("notes.txt", b"hello")])
    assert r.status_code == 415
    assert "notes.txt" in r.json()["detail"]
    assert "PDF" in r.json()["detail"]
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_upload_rejects_renamed_file(client, app, subject_id):
    r = _upload(client, subject_id, [_pdf("fake.pdf", b"just text here")])
    assert r.status_code == 415
    assert _material_count(app) == 0


def test_upload_rejects_old_word_doc(client, subject_id):
    r = _upload(client, subject_id, [_pdf("old.doc", b"\xd0\xcf\x11\xe0")])
    assert r.status_code == 415
    assert ".docx" in r.json()["detail"]


def test_mixed_upload_with_one_bad_file_stores_nothing(
    client, app, settings, subject_id
):
    r = _upload(client, subject_id, [_pdf(), _pdf("bad.txt", b"hello")])
    assert r.status_code == 415
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_upload_too_large_is_413(client, app, settings, subject_id):
    settings.upload_max_mb = 0
    r = _upload(client, subject_id, [_pdf()])
    assert r.status_code == 413
    assert _material_count(app) == 0


def test_upload_empty_file_is_422(client, subject_id):
    r = _upload(client, subject_id, [_pdf("empty.pdf", b"")])
    assert r.status_code == 422
    assert "empty.pdf" in r.json()["detail"]


def test_upload_without_files_is_422(client, subject_id):
    r = client.post(f"/api/v1/subjects/{subject_id}/materials", data={"title": "x"})
    assert r.status_code == 422


def test_upload_too_many_files_is_422(client, settings, subject_id):
    settings.upload_max_files = 1
    r = _upload(client, subject_id, [_pdf("a.pdf"), _pdf("b.pdf")])
    assert r.status_code == 422
    assert "at most 1" in r.json()["detail"]


def test_upload_to_missing_subject_is_404(client, app):
    r = _upload(client, 99, [_pdf()])
    assert r.status_code == 404
    assert _material_count(app) == 0


def test_upload_failure_leaves_no_rows_or_files(
    client, app, settings, subject_id, monkeypatch: pytest.MonkeyPatch
):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("learnmate.api.materials.shutil.copyfileobj", boom)
    with pytest.raises(OSError):
        _upload(client, subject_id, [_pdf()])
    assert _material_count(app) == 0
    assert _stored(settings) == []


def test_get_material_returns_status_pages_and_chapters(
    client, app, subject_id, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(ingest, "ingest", lambda *args, **kwargs: None)
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    with app.state.session_factory() as db:
        material = db.get(Material, mid)
        material.pages_total, material.pages_read = 4, 2
        db.add(Chapter(material_id=mid, name="Second", position=2))
        db.add(Chapter(material_id=mid, name="First", position=1))
        db.commit()
    body = client.get(f"/api/v1/materials/{mid}").json()
    assert (body["status"], body["pages_read"], body["pages_total"]) == (
        "reading",
        2,
        4,
    )
    assert [c["name"] for c in body["chapters"]] == ["First", "Second"]


def test_get_missing_material_is_404(client):
    assert client.get("/api/v1/materials/99").status_code == 404


def test_list_subject_materials_newest_first(client, subject_id):
    first = _upload(client, subject_id, [_pdf("a.pdf")]).json()["id"]
    second = _upload(client, subject_id, [_pdf("b.pdf")]).json()["id"]
    rows = client.get(f"/api/v1/subjects/{subject_id}/materials").json()
    assert [m["id"] for m in rows] == [second, first]
    assert client.get("/api/v1/subjects/99/materials").status_code == 404


def test_delete_material_removes_rows_and_files(client, app, settings, subject_id):
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    with app.state.session_factory() as db:
        chapter = Chapter(material_id=mid, name="C", position=1)
        db.add(chapter)
        db.flush()
        db.add(Chunk(material_id=mid, chapter_id=chapter.id, position=1, text="t"))
        db.commit()
    assert client.delete(f"/api/v1/materials/{mid}").status_code == 204
    with app.state.session_factory() as db:
        for model in (Material, MaterialFile, Chapter, Chunk):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert db.get(Subject, subject_id) is not None
    assert not (settings.data_dir / "files" / str(mid)).exists()
    assert client.delete(f"/api/v1/materials/{mid}").status_code == 404


def _figure(app, mid, path):
    with app.state.session_factory() as db:
        fig = Figure(material_id=mid, path=path, description="d")
        db.add(fig)
        db.commit()
        return fig.id


def test_get_figure_serves_image(client, app, settings, subject_id):
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    (settings.data_dir / "files" / str(mid) / "fig.png").write_bytes(PNG)
    fid = _figure(app, mid, f"{mid}/fig.png")
    r = client.get(f"/api/v1/figures/{fid}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == PNG


def test_get_figure_missing_file_is_404(client, app, subject_id):
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    assert (
        client.get(f"/api/v1/figures/{_figure(app, mid, f'{mid}/no.png')}").status_code
        == 404
    )
    assert client.get("/api/v1/figures/99").status_code == 404


def test_get_figure_outside_files_dir_is_404(client, app, settings, subject_id):
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    (settings.data_dir / "secret.txt").write_text("secret")
    fid = _figure(app, mid, "../secret.txt")
    assert client.get(f"/api/v1/figures/{fid}").status_code == 404


def test_material_endpoints_require_device_token(app, subject_id):
    with TestClient(app) as bare:
        r = bare.post(
            f"/api/v1/subjects/{subject_id}/materials",
            files=[_pdf()],
        )
        assert r.status_code == 401
        assert bare.get("/api/v1/figures/1").status_code == 401


@pytest.mark.parametrize(
    ("name", "head", "mime"),
    [
        ("a.pdf", PDF, "application/pdf"),
        (
            "a.docx",
            DOCX,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("a.jpg", b"\xff\xd8\xff\xe0", "image/jpeg"),
        ("a.JPEG", b"\xff\xd8\xff\xe0", "image/jpeg"),
        ("a.png", PNG, "image/png"),
        ("a.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
    ],
)
def test_sniff_accepts_each_allowed_type(name, head, mime):
    assert sniff(name, head)[1] == mime


@pytest.mark.parametrize("name", ["a.heic", "noext", "a.txt"])
def test_sniff_rejects_other_types(name):
    with pytest.raises(UnsupportedFile, match="PDF"):
        sniff(name, PDF)


def test_resolve_stored_rejects_escape(settings):
    assert resolve_stored(settings.data_dir, "1/a.png").name == "a.png"
    with pytest.raises(ValueError):
        resolve_stored(settings.data_dir, "../learnmate.db")


def test_delete_material_removes_figure_file_and_endpoint_404s(
    client, app, settings, subject_id
):
    mid = _upload(client, subject_id, [_pdf()]).json()["id"]
    path = settings.data_dir / "files" / str(mid) / "fig-001-1.png"
    path.write_bytes(PNG)
    fid = _figure(app, mid, f"{mid}/fig-001-1.png")
    r = client.get(f"/api/v1/figures/{fid}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert client.delete(f"/api/v1/materials/{mid}").status_code == 204
    assert client.get(f"/api/v1/figures/{fid}").status_code == 404
    assert not path.exists()
