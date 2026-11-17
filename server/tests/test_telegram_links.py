from sqlalchemy.orm import Session

from learnmate.models import Family
from learnmate.telegram.links import TelegramHooks, handle_new_pin, link_chat
from learnmate.telegram.templates import NEW_PIN_UNAVAILABLE, NOT_LINKED


def _family(db: Session, code: str | None = "abc123", chat_id: int | None = None):
    family = Family(
        id=1,
        child_name="Maya",
        grade=7,
        telegram_chat_id=chat_id,
        telegram_link_code=code,
    )
    db.add(family)
    db.commit()
    return family


def test_start_with_valid_code_links_chat(db: Session):
    family = _family(db)
    assert link_chat(db, "abc123", 42) is True
    assert family.telegram_chat_id == 42
    assert family.telegram_link_code is None


def test_start_with_invalid_code_is_refused(db: Session):
    family = _family(db)
    assert link_chat(db, "wrong", 42) is False
    assert link_chat(db, "", 42) is False
    family.telegram_link_code = None
    db.commit()
    assert link_chat(db, "abc123", 42) is False
    assert family.telegram_chat_id is None


def test_start_without_family_is_refused(db: Session):
    assert link_chat(db, "abc123", 42) is False


def test_code_works_once(db: Session):
    _family(db)
    assert link_chat(db, "abc123", 42) is True
    assert link_chat(db, "abc123", 43) is False


def test_new_pin_calls_hook_with_session_id(db: Session):
    _family(db, chat_id=42)
    calls = []

    def hook(_db, session_id):
        calls.append(session_id)
        return "Sent"

    assert handle_new_pin(db, TelegramHooks(new_pin=hook), 42, "new_pin:12") == "Sent"
    assert calls == [12]


def test_new_pin_from_other_chat_refused(db: Session):
    _family(db, chat_id=42)
    calls = []
    hooks = TelegramHooks(new_pin=lambda _db, i: calls.append(i) or "x")
    assert handle_new_pin(db, hooks, 99, "new_pin:12") == NOT_LINKED
    assert calls == []


def test_new_pin_without_family_refused(db: Session):
    assert handle_new_pin(db, TelegramHooks(), 42, "new_pin:12") == NOT_LINKED


def test_new_pin_without_hook_unavailable(db: Session):
    _family(db, chat_id=42)
    assert handle_new_pin(db, TelegramHooks(), 42, "new_pin:12") == NEW_PIN_UNAVAILABLE


def test_new_pin_bad_data_unavailable(db: Session):
    _family(db, chat_id=42)
    calls = []
    hooks = TelegramHooks(new_pin=lambda _db, i: calls.append(i) or "x")
    for data in ("new_pin:abc", "new_pin:", "other:1", "new_pin:-1"):
        assert handle_new_pin(db, hooks, 42, data) == NEW_PIN_UNAVAILABLE
    assert calls == []
