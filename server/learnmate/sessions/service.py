"""Session set-up: create, replace the PIN, start, and the Telegram New PIN handler."""

import json
from dataclasses import dataclass
from typing import Literal

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.budget import require_budget
from learnmate.models import (
    Chapter,
    Family,
    Material,
    SessionChapter,
    SessionEvent,
    SessionMaterial,
    StudySession,
    Subject,
)
from learnmate.sessions.pins import generate_pin, read_pin, set_pin
from learnmate.telegram import templates
from learnmate.telegram.outbox import enqueue

ACTIVE_STATES = ("set_up", "running", "locked")
QUESTION_COUNTS = (5, 10, 15)


class SessionError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class NewSession:
    subject_id: int
    type: str  # one of models.SESSION_TYPES
    material_ids: tuple[int, ...]
    chapter_ids: tuple[int, ...]
    question_count: int


def _family(db: Session) -> Family:
    family = db.get(Family, FAMILY_ID)
    if family is None:
        raise SessionError(409, "Family not set up")
    return family


def _check_scope(
    db: Session, req: NewSession, materials: list[int], chapters: list[int]
) -> None:
    if req.type in ("recap", "test_only"):
        if not chapters:
            raise SessionError(422, "Pick at least one chapter")
    elif not materials and not chapters:
        raise SessionError(422, "Pick material or chapters")
    found_materials = db.scalars(
        select(Material.id).where(
            Material.id.in_(materials), Material.subject_id == req.subject_id
        )
    ).all()
    found_chapters = db.scalars(
        select(Chapter.id)
        .join(Material, Chapter.material_id == Material.id)
        .where(Chapter.id.in_(chapters), Material.subject_id == req.subject_id)
    ).all()
    if len(found_materials) != len(materials) or len(found_chapters) != len(chapters):
        raise SessionError(422, "Material or chapter not in this subject")


def create_session(
    db: Session, settings: Settings, clock: Clock, cipher: Fernet, req: NewSession
) -> tuple[StudySession, str]:
    family = _family(db)
    require_budget(db, settings, clock)
    if db.get(Subject, req.subject_id) is None:
        raise SessionError(422, "Subject not found")
    materials = sorted(set(req.material_ids))
    chapters = sorted(set(req.chapter_ids))
    _check_scope(db, req, materials, chapters)
    busy = db.scalar(
        select(StudySession.id)
        .where(StudySession.state.in_(("running", "locked")))
        .limit(1)
    )
    if busy is not None:
        raise SessionError(409, "A session is already running")
    for old in db.scalars(select(StudySession).where(StudySession.state == "set_up")):
        old.state = "cancelled"
        old.pin_hash = None
        old.pin_enc = None
    row = StudySession(
        subject_id=req.subject_id,
        type=req.type,
        question_count=req.question_count,
        state="set_up",
        pin_version=1,
    )
    db.add(row)
    db.flush()
    db.add_all(SessionMaterial(session_id=row.id, material_id=m) for m in materials)
    db.add_all(SessionChapter(session_id=row.id, chapter_id=c) for c in chapters)
    pin = generate_pin(settings.pin_length)
    set_pin(row, pin, cipher)
    row.pin_last_sent_at = clock.now()
    enqueue(db, templates.session_pin(family.child_name, pin, row.id, "new"))
    db.commit()
    return row, pin


def replace_pin(
    db: Session,
    settings: Settings,
    clock: Clock,
    cipher: Fernet,
    session_id: int,
    *,
    via: Literal["app", "telegram"],
) -> tuple[StudySession, str]:
    row = db.get(StudySession, session_id)
    if row is None:
        raise SessionError(404, "Session not found")
    if row.state not in ACTIVE_STATES:
        raise SessionError(409, "Session is not active")
    family = _family(db)
    pin = generate_pin(settings.pin_length, avoid=read_pin(row, cipher))
    set_pin(row, pin, cipher)
    row.pin_version += 1
    row.pin_last_sent_at = clock.now()
    db.add(
        SessionEvent(
            session_id=row.id,
            type="pin_replaced",
            data_json=json.dumps({"pin_version": row.pin_version, "via": via}),
        )
    )
    enqueue(db, templates.session_pin(family.child_name, pin, row.id, "replaced"))
    db.commit()
    return row, pin


def start_session(
    db: Session, settings: Settings, clock: Clock, session_id: int
) -> StudySession:
    row = db.get(StudySession, session_id)
    if row is None:
        raise SessionError(404, "Session not found")
    if row.state != "set_up":
        raise SessionError(409, "Session is not waiting to start")
    family = _family(db)
    now = clock.now()
    row.state = "running"
    row.started_at = now
    db.add(SessionEvent(session_id=row.id, type="started"))
    subject = db.get(Subject, row.subject_id) if row.subject_id else None
    enqueue(
        db,
        templates.session_started(
            family.child_name,
            subject.name if subject else "study",
            templates.clock_time(now, settings.timezone),
        ),
    )
    db.commit()
    return row


def current_session(db: Session) -> StudySession | None:
    return db.scalars(
        select(StudySession)
        .where(StudySession.state.in_(ACTIVE_STATES))
        .order_by(StudySession.id.desc())
        .limit(1)
    ).first()


def scope_ids(db: Session, row: StudySession) -> tuple[list[int], list[int]]:
    materials = db.scalars(
        select(SessionMaterial.material_id)
        .where(SessionMaterial.session_id == row.id)
        .order_by(SessionMaterial.material_id)
    ).all()
    chapters = db.scalars(
        select(SessionChapter.chapter_id)
        .where(SessionChapter.session_id == row.id)
        .order_by(SessionChapter.chapter_id)
    ).all()
    return list(materials), list(chapters)


def telegram_new_pin(
    db: Session,
    session_id: int,
    *,
    settings: Settings,
    clock: Clock,
    cipher: Fernet,
) -> str:
    try:
        replace_pin(db, settings, clock, cipher, session_id, via="telegram")
    except SessionError:
        return templates.NEW_PIN_UNAVAILABLE
    return templates.NEW_PIN_SENT
