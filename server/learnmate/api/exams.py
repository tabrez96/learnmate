"""Exam dates per subject."""

import datetime as dt

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.api.deps import AppSettings, DbSession
from learnmate.models import Exam, Subject
from learnmate.plan.service import local_date

router = APIRouter(prefix="/api/v1")


class ExamIn(BaseModel):
    subject_id: int
    date: dt.date


class ExamPatch(BaseModel):
    subject_id: int | None = None
    date: dt.date | None = None


class ExamOut(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    date: dt.date


def _out(db: Session, exam: Exam) -> ExamOut:
    subject = db.get(Subject, exam.subject_id)
    return ExamOut(
        id=exam.id,
        subject_id=exam.subject_id,
        subject_name=subject.name if subject else "",
        date=exam.date,
    )


def _check(
    db: Session,
    request: Request,
    settings: AppSettings,
    subject_id: int,
    date: dt.date,
    exam_id: int | None,
) -> None:
    if db.get(Subject, subject_id) is None:
        raise HTTPException(422, "Subject not found")
    if date < local_date(request.app.state.clock.now(), settings.timezone):
        raise HTTPException(422, "Exam date is in the past")
    query = select(Exam.id).where(Exam.subject_id == subject_id, Exam.date == date)
    if exam_id is not None:
        query = query.where(Exam.id != exam_id)
    if db.scalar(query) is not None:
        raise HTTPException(409, "This subject already has an exam on that date")


@router.get("/exams")
def list_exams(db: DbSession, subject_id: int | None = None) -> list[ExamOut]:
    query = (
        select(Exam, Subject.name)
        .join(Subject, Subject.id == Exam.subject_id)
        .order_by(Exam.date, Exam.id)
    )
    if subject_id is not None:
        query = query.where(Exam.subject_id == subject_id)
    return [
        ExamOut(id=e.id, subject_id=e.subject_id, subject_name=name, date=e.date)
        for e, name in db.execute(query)
    ]


@router.post("/exams", status_code=201)
def create_exam(
    body: ExamIn, request: Request, db: DbSession, settings: AppSettings
) -> ExamOut:
    _check(db, request, settings, body.subject_id, body.date, None)
    exam = Exam(subject_id=body.subject_id, date=body.date)
    db.add(exam)
    db.commit()
    return _out(db, exam)


@router.patch("/exams/{exam_id}")
def update_exam(
    exam_id: int,
    body: ExamPatch,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> ExamOut:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(404, "Exam not found")
    subject_id = body.subject_id if body.subject_id is not None else exam.subject_id
    date = body.date if body.date is not None else exam.date
    _check(db, request, settings, subject_id, date, exam.id)
    exam.subject_id = subject_id
    exam.date = date
    db.commit()
    return _out(db, exam)


@router.delete("/exams/{exam_id}", status_code=204)
def delete_exam(exam_id: int, db: DbSession) -> Response:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(404, "Exam not found")
    db.delete(exam)
    db.commit()
    return Response(status_code=204)
