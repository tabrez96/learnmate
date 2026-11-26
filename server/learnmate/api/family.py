"""First run and settings: the family row, the fallback password and the Telegram link code."""

import secrets
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from learnmate.api.deps import AppSettings, DbSession
from learnmate.models import Family
from learnmate.passwords import hash_password, verify_password

FAMILY_ID = 1

router = APIRouter(prefix="/api/v1")


class FamilyIn(BaseModel):
    child_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    grade: int = Field(ge=5, le=10)
    outside_books_allowed: bool | None = None
    inactivity_warn_s: int | None = Field(None, ge=30, le=3600)
    inactivity_lock_s: int | None = Field(None, ge=60, le=3600)


class FamilyOut(BaseModel):
    child_name: str
    grade: int
    outside_books_allowed: bool
    inactivity_warn_s: int
    inactivity_lock_s: int
    telegram_connected: bool
    telegram_handle: str | None
    fallback_set: bool


class FallbackIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    current_password: str | None = None


class TelegramCodeOut(BaseModel):
    code: str


def _get_family(db: Session) -> Family | None:
    return db.get(Family, FAMILY_ID)


def _require_family(db: Session) -> Family:
    family = _get_family(db)
    if family is None:
        raise HTTPException(409, "Family not set up")
    return family


def _to_out(family: Family) -> FamilyOut:
    return FamilyOut(
        child_name=family.child_name,
        grade=family.grade,
        outside_books_allowed=family.outside_books_allowed,
        inactivity_warn_s=family.inactivity_warn_s,
        inactivity_lock_s=family.inactivity_lock_s,
        telegram_connected=family.telegram_chat_id is not None,
        telegram_handle=(
            family.telegram_handle if family.telegram_chat_id is not None else None
        ),
        fallback_set=family.fallback_hash is not None,
    )


@router.get("/family")
def get_family(db: DbSession) -> FamilyOut:
    family = _get_family(db)
    if family is None:
        raise HTTPException(404, "Family not set up")
    return _to_out(family)


@router.put("/family")
def put_family(body: FamilyIn, db: DbSession, settings: AppSettings) -> FamilyOut:
    family = _get_family(db)
    if family is None:
        family = Family(
            id=FAMILY_ID,
            child_name=body.child_name,
            grade=body.grade,
            outside_books_allowed=True,
            inactivity_warn_s=settings.inactivity_warn_seconds,
            inactivity_lock_s=settings.inactivity_lock_seconds,
        )
        db.add(family)
    else:
        family.child_name = body.child_name
        family.grade = body.grade
    if body.outside_books_allowed is not None:
        family.outside_books_allowed = body.outside_books_allowed
    if body.inactivity_warn_s is not None:
        family.inactivity_warn_s = body.inactivity_warn_s
    if body.inactivity_lock_s is not None:
        family.inactivity_lock_s = body.inactivity_lock_s
    if family.inactivity_warn_s >= family.inactivity_lock_s:
        db.rollback()
        raise HTTPException(422, "inactivity_warn_s must be below inactivity_lock_s")
    db.commit()
    return _to_out(family)


@router.put("/family/fallback", status_code=204)
def put_fallback(body: FallbackIn, db: DbSession) -> Response:
    family = _require_family(db)
    if family.fallback_hash is not None and not verify_password(
        body.current_password or "", family.fallback_hash
    ):
        raise HTTPException(403, "Current password is wrong")
    family.fallback_hash = hash_password(body.password)
    family.fallback_wrong = 0
    family.fallback_locked_until = None
    db.commit()
    return Response(status_code=204)


@router.post("/family/telegram-code", status_code=201)
def create_telegram_code(db: DbSession) -> TelegramCodeOut:
    family = _require_family(db)
    code = secrets.token_hex(8)
    family.telegram_link_code = code
    db.commit()
    return TelegramCodeOut(code=code)
