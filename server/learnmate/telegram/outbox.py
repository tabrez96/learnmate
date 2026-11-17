"""Database outbox: queue messages, deliver them with retries and backoff."""

import json
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from learnmate.api.family import FAMILY_ID
from learnmate.clock import Clock
from learnmate.models import Family, Outbox
from learnmate.telegram.sender import Sender, SendError
from learnmate.telegram.templates import Button, OutMessage

log = logging.getLogger(__name__)

BACKOFF_SECONDS = (5, 15, 60, 300)
MAX_BACKOFF_SECONDS = 900
BATCH = 20


def backoff_seconds(attempts: int) -> int:
    """Wait after `attempts` failures so far (at least 1)."""
    if attempts <= len(BACKOFF_SECONDS):
        return BACKOFF_SECONDS[max(attempts, 1) - 1]
    return MAX_BACKOFF_SECONDS


def enqueue(db: Session, message: OutMessage) -> Outbox:
    """Queue a message. Flushes but does not commit: the caller commits with its own change."""
    buttons = [{"text": b.text, "data": b.data} for b in message.buttons]
    row = Outbox(
        text=message.text,
        buttons_json=json.dumps(buttons) if buttons else None,
        status="pending",
    )
    db.add(row)
    db.flush()
    return row


def _buttons(row: Outbox) -> tuple[Button, ...]:
    if not row.buttons_json:
        return ()
    return tuple(Button(b["text"], b["data"]) for b in json.loads(row.buttons_json))


async def deliver_due(db: Session, sender: Sender, clock: Clock) -> int:
    """Send pending messages that are due, oldest first, stopping at one that is not due yet. Returns how many were sent."""
    family = db.get(Family, FAMILY_ID)
    if family is None or family.telegram_chat_id is None:
        return 0
    now = clock.now()
    rows = db.scalars(
        select(Outbox)
        .where(Outbox.status == "pending")
        .order_by(Outbox.id)
        .limit(BATCH)
    ).all()
    sent = 0
    for row in rows:
        if row.next_try_at is not None and row.next_try_at > now:
            break  # the oldest message is waiting to be retried; keep order
        try:
            await sender.send(
                family.telegram_chat_id, OutMessage(row.text, _buttons(row))
            )
        except SendError as e:
            row.attempts += 1
            row.next_try_at = clock.now() + timedelta(
                seconds=backoff_seconds(row.attempts)
            )
            db.commit()
            log.warning("Telegram send failed (attempt %s): %s", row.attempts, e)
            break
        row.status = "sent"
        row.attempts += 1
        db.commit()
        sent += 1
    return sent
