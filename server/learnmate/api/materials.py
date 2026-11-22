"""Material: upload into a subject, reading status, delete, and figure images."""

import datetime as dt
import mimetypes
import shutil
from pathlib import Path
from typing import Annotated, BinaryIO

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from learnmate import ingest
from learnmate.api.deps import AppSettings, DbSession
from learnmate.classroom import (
    ClassroomError,
    InvalidLink,
    fetch_coursework,
    parse_link,
)
from learnmate.config import Settings
from learnmate.files import (
    UnsupportedFile,
    material_dir,
    remove_material_dirs,
    resolve_stored,
    sniff,
)
from learnmate.models import Chapter, Figure, Material, MaterialFile, Subject

router = APIRouter(prefix="/api/v1")


class ChapterOut(BaseModel):
    id: int
    name: str
    position: int


class MaterialOut(BaseModel):
    id: int
    subject_id: int
    title: str
    kind: str
    status: str
    error: str | None
    pages_read: int
    pages_total: int | None
    chapters_hint: str | None
    chapters: list[ChapterOut]
    file_types: list[str]
    created_at: dt.datetime


def _to_out(db: Session, material: Material) -> MaterialOut:
    chapters = db.scalars(
        select(Chapter)
        .where(Chapter.material_id == material.id)
        .order_by(Chapter.position, Chapter.id)
    )
    mimes = db.scalars(
        select(MaterialFile.mime)
        .where(MaterialFile.material_id == material.id)
        .order_by(MaterialFile.id)
    )
    return MaterialOut(
        id=material.id,
        subject_id=material.subject_id,
        title=material.title,
        kind=material.kind,
        status=material.status,
        error=material.error,
        pages_read=material.pages_read,
        pages_total=material.pages_total,
        chapters_hint=material.chapters_hint,
        chapters=[
            ChapterOut(id=c.id, name=c.name, position=c.position) for c in chapters
        ],
        file_types=list(mimes),
        created_at=material.created_at,
    )


def _check_subject(db: Session, subject_id: int) -> None:
    if db.get(Subject, subject_id) is None:
        raise HTTPException(404, "Subject not found")


def _store_material(
    db: Session,
    settings: Settings,
    material: Material,
    files: list[tuple[BinaryIO, str, str, int]],
) -> None:
    try:
        db.add(material)
        db.flush()
        directory = material_dir(settings.data_dir, material.id)
        directory.mkdir(parents=True, exist_ok=True)
        for i, (f, ext, mime, size) in enumerate(files, start=1):
            with open(directory / f"{i:02d}{ext}", "wb") as out:
                shutil.copyfileobj(f, out)
            db.add(
                MaterialFile(
                    material_id=material.id,
                    path=f"{material.id}/{i:02d}{ext}",
                    mime=mime,
                    size=size,
                )
            )
        db.commit()
    except BaseException:
        # SQLite can hand a rolled-back id to the next upload, so clean up
        # while this transaction still holds the id, then roll back.
        try:
            if material.id is not None:
                remove_material_dirs(settings.data_dir, [material.id])
        finally:
            db.rollback()
        raise


def _start_ingest(
    request: Request,
    background: BackgroundTasks,
    settings: Settings,
    material_id: int,
) -> None:
    background.add_task(
        ingest.ingest,
        request.app.state.session_factory,
        settings,
        material_id,
        llm=request.app.state.llm,
        embedder=request.app.state.embedder,
        clock=request.app.state.clock,
    )


@router.post("/subjects/{subject_id}/materials", status_code=201)
def upload_material(
    subject_id: int,
    db: DbSession,
    settings: AppSettings,
    request: Request,
    background: BackgroundTasks,
    files: Annotated[list[UploadFile], File()],
    title: Annotated[str | None, Form(max_length=200)] = None,
    chapters: Annotated[str | None, Form(max_length=2000)] = None,
) -> MaterialOut:
    # The only place material is created, so it always belongs to a subject.
    _check_subject(db, subject_id)
    if not files:
        raise HTTPException(422, "Add at least one file")
    if len(files) > settings.upload_max_files:
        raise HTTPException(
            422, f"Upload at most {settings.upload_max_files} files at a time"
        )

    # Validate every file before writing anything.
    checked: list[tuple[UploadFile, str, str, int]] = []
    for f in files:
        name = f.filename or "file"
        head = f.file.read(16)
        f.file.seek(0, 2)
        size = f.file.tell()
        f.file.seek(0)
        if size == 0:
            raise HTTPException(422, f"{name} is empty")
        try:
            ext, mime = sniff(name, head)
        except UnsupportedFile as exc:
            raise HTTPException(415, str(exc)) from exc
        if size > settings.upload_max_mb * 1024 * 1024:
            raise HTTPException(
                413, f"{name} is larger than {settings.upload_max_mb} MB"
            )
        checked.append((f, ext, mime, size))

    first_name = Path(files[0].filename or "").stem[:200]
    material = Material(
        subject_id=subject_id,
        title=(title or "").strip() or first_name or "Material",
        kind="upload",
        status="reading",
        chapters_hint=(chapters or "").strip() or None,
    )
    _store_material(
        db,
        settings,
        material,
        [(f.file, ext, mime, size) for f, ext, mime, size in checked],
    )
    _start_ingest(request, background, settings, material.id)
    return _to_out(db, material)


class ClassroomIn(BaseModel):
    link: str = Field(max_length=2000)
    access_token: SecretStr
    title: str | None = Field(None, max_length=200)
    chapters: str | None = Field(None, max_length=2000)


def classroom_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ClassroomError)
    return JSONResponse(
        status_code=exc.status, content={"error": exc.code, "detail": str(exc)}
    )


@router.post("/subjects/{subject_id}/materials/classroom", status_code=201)
def add_classroom_material(
    subject_id: int,
    body: ClassroomIn,
    db: DbSession,
    settings: AppSettings,
    request: Request,
    background: BackgroundTasks,
) -> MaterialOut:
    # The token lives only in this request: it is used for the download and
    # never stored or logged.
    _check_subject(db, subject_id)
    token = body.access_token.get_secret_value().strip()
    if not token:
        raise HTTPException(422, "Sign in to Google first")
    try:
        link = parse_link(body.link)
    except InvalidLink:
        raise ClassroomError(
            "classroom_link_invalid",
            422,
            "This isn't a Google Classroom assignment or material link. "
            "Open the post in Classroom, copy its link and paste it here.",
        ) from None
    coursework = fetch_coursework(
        link,
        token,
        max_bytes=settings.upload_max_mb * 1024 * 1024,
        max_files=settings.upload_max_files,
        transport=request.app.state.google_transport,
    )
    material = Material(
        subject_id=subject_id,
        title=(body.title or "").strip()[:200]
        or coursework.title[:200]
        or "Classroom material",
        kind="classroom",
        source_url=link.url,
        status="reading",
        chapters_hint=(body.chapters or "").strip() or None,
    )
    try:
        _store_material(
            db,
            settings,
            material,
            [(d.file, d.ext, d.mime, d.size) for d in coursework.downloads],
        )
    finally:
        for d in coursework.downloads:
            d.file.close()
    _start_ingest(request, background, settings, material.id)
    return _to_out(db, material)


@router.get("/subjects/{subject_id}/materials")
def list_materials(subject_id: int, db: DbSession) -> list[MaterialOut]:
    _check_subject(db, subject_id)
    rows = db.scalars(
        select(Material)
        .where(Material.subject_id == subject_id)
        .order_by(Material.created_at.desc(), Material.id.desc())
    )
    return [_to_out(db, m) for m in rows]


@router.get("/materials/{material_id}")
def get_material(material_id: int, db: DbSession) -> MaterialOut:
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "Material not found")
    return _to_out(db, material)


@router.delete("/materials/{material_id}", status_code=204)
def delete_material(material_id: int, db: DbSession, settings: AppSettings) -> Response:
    if db.get(Material, material_id) is None:
        raise HTTPException(404, "Material not found")
    db.execute(delete(Material).where(Material.id == material_id))
    db.commit()
    remove_material_dirs(settings.data_dir, [material_id])
    return Response(status_code=204)


@router.get("/figures/{figure_id}")
def get_figure(figure_id: int, db: DbSession, settings: AppSettings) -> FileResponse:
    figure = db.get(Figure, figure_id)
    if figure is None:
        raise HTTPException(404, "Figure not found")
    try:
        path = resolve_stored(settings.data_dir, figure.path)
    except ValueError:
        raise HTTPException(404, "Figure not found") from None
    if not path.is_file():
        raise HTTPException(404, "Figure not found")
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    )
