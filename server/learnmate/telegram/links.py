"""Chat linking and the "New PIN" callback, free of Telegram types."""

import secrets
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.models import Family
from learnmate.telegram.templates import (
    NEW_PIN_PREFIX,
    NEW_PIN_UNAVAILABLE,
    NOT_LINKED,
)

# (db, session_id) -> reply shown to the parent; queues the new PIN message itself.
NewPinHandler = Callable[[Session, int], str]


@dataclass
class TelegramHooks:
    new_pin: NewPinHandler | None = None


def link_chat(db: Session, code: str, chat_id: int) -> bool:
    family = db.get(Family, FAMILY_ID)
    if family is None or not family.telegram_link_code or not code:
        return False
    if not secrets.compare_digest(code.encode(), family.telegram_link_code.encode()):
        return False
    family.telegram_chat_id = chat_id
    family.telegram_link_code = None
    db.commit()
    return True


def handle_new_pin(db: Session, hooks: TelegramHooks, chat_id: int, data: str) -> str:
    family = db.get(Family, FAMILY_ID)
    if family is None or family.telegram_chat_id != chat_id:
        return NOT_LINKED
    raw = data.removeprefix(NEW_PIN_PREFIX)
    if raw == data or not raw.isascii() or not raw.isdigit():
        return NEW_PIN_UNAVAILABLE
    if hooks.new_pin is None:
        return NEW_PIN_UNAVAILABLE
    return hooks.new_pin(db, int(raw))
