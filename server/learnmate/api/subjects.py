"""Subjects: list with material counts and grades, create, rename and delete."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, StringConstraints
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from learnmate.api.deps import AppSettings, DbSession
from learnmate.files import remove_material_dirs
from learnmate.models import Material, StudyTest, Subject

router = APIRouter(prefix="/api/v1")

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Icon = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]

ICON_KEYWORDS = (
    ("math", "calculator"),
    ("science", "flask"),
    ("physic", "atom"),
    ("chem", "flask"),
    ("bio", "leaf"),
    ("history", "landmark"),
    ("geo", "globe"),
    ("english", "book-open"),
    ("computer", "laptop"),
)


class SubjectIn(BaseModel):
    name: Name
    icon: Icon | None = None


class SubjectPatch(BaseModel):
    name: Name | None = None
    icon: Icon | None = None


class GradeOut(BaseModel):
    status: str
    score_pct: int | None
    band: str | None
    at: dt.datetime


class SubjectOut(BaseModel):
    id: int
    name: str
    icon: str
    material_count: int
    latest_grade: GradeOut | None
    average_pct: int | None


def default_icon(name: str) -> str:
    lowered = name.lower()
    for keyword, icon in ICON_KEYWORDS:
        if keyword in lowered:
            return icon
    return "book"


def _name_taken(db: Session, name: str, exclude_id: int | None = None) -> None:
    # SQLite lower() is ASCII-only, so compare casefolded names in Python.
    query = select(Subject.id, Subject.name)
    if exclude_id is not None:
        query = query.where(Subject.id != exclude_id)
    wanted = name.casefold()
    if any(existing.casefold() == wanted for _, existing in db.execute(query)):
        raise HTTPException(409, "A subject with this name already exists")


def _counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Material.subject_id, func.count()).group_by(Material.subject_id)
    )
    return {subject_id: count for subject_id, count in rows}


def _to_out(db: Session, subject: Subject, counts: dict[int, int]) -> SubjectOut:
    graded = (StudyTest.subject_id == subject.id, StudyTest.graded.is_(True))
    latest = db.scalars(
        select(StudyTest)
        .where(*graded, StudyTest.status.in_(("done", "missed")))
        .order_by(
            func.coalesce(StudyTest.finished_at, StudyTest.created_at).desc(),
            StudyTest.id.desc(),
        )
        .limit(1)
    ).first()
    average = db.scalar(
        select(func.avg(StudyTest.score_pct)).where(*graded, StudyTest.status == "done")
    )
    grade = None
    if latest is not None:
        grade = GradeOut(
            status=latest.status,
            score_pct=latest.score_pct if latest.status == "done" else None,
            band=latest.band if latest.status == "done" else None,
            at=latest.finished_at or latest.created_at,
        )
    return SubjectOut(
        id=subject.id,
        name=subject.name,
        icon=subject.icon,
        material_count=counts.get(subject.id, 0),
        latest_grade=grade,
        average_pct=None if average is None else round(average),
    )


def _get_subject(db: Session, subject_id: int) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(404, "Subject not found")
    return subject


@router.get("/subjects")
def list_subjects(db: DbSession) -> list[SubjectOut]:
    counts = _counts(db)
    subjects = db.scalars(select(Subject).order_by(Subject.created_at, Subject.id))
    return [_to_out(db, s, counts) for s in subjects]


@router.post("/subjects", status_code=201)
def create_subject(body: SubjectIn, db: DbSession) -> SubjectOut:
    _name_taken(db, body.name)
    subject = Subject(name=body.name, icon=body.icon or default_icon(body.name))
    db.add(subject)
    db.commit()
    return _to_out(db, subject, {})


@router.patch("/subjects/{subject_id}")
def patch_subject(subject_id: int, body: SubjectPatch, db: DbSession) -> SubjectOut:
    subject = _get_subject(db, subject_id)
    if body.name is not None:
        _name_taken(db, body.name, exclude_id=subject.id)
        subject.name = body.name
    if body.icon is not None:
        subject.icon = body.icon
    db.commit()
    return _to_out(db, subject, _counts(db))


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: DbSession, settings: AppSettings) -> Response:
    _get_subject(db, subject_id)
    # Foreign keys cascade to material, material_file, chapter, figure, chunk
    # (the chunk_fts trigger clears search), exam, session_material and
    # session_chapter. session.subject_id and test.subject_id are SET NULL, so
    # tests and grades stay. Rows go first, then files, so a failed file removal
    # never leaves rows pointing at missing files.
    material_ids = list(
        db.scalars(select(Material.id).where(Material.subject_id == subject_id))
    )
    db.execute(delete(Subject).where(Subject.id == subject_id))
    db.commit()
    remove_material_dirs(settings.data_dir, material_ids)
    return Response(status_code=204)
