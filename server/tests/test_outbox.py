import asyncio
import datetime as dt

from sqlalchemy.orm import Session

from learnmate.clock import FakeClock
from learnmate.models import Family, Outbox
from learnmate.telegram.outbox import backoff_seconds, deliver_due, enqueue
from learnmate.telegram.sender import FakeSender, SendError
from learnmate.telegram.templates import Button, OutMessage


def _family(db: Session, chat_id: int | None = 555) -> None:
    db.add(Family(id=1, child_name="Maya", grade=7, telegram_chat_id=chat_id))
    db.commit()


def test_enqueue_stores_text_and_buttons(db: Session):
    row = enqueue(db, OutMessage("hi", (Button("New PIN", "new_pin:1"),)))
    db.commit()
    assert row.status == "pending"
    assert row.text == "hi"
    assert row.buttons_json == '[{"text": "New PIN", "data": "new_pin:1"}]'
    assert enqueue(db, OutMessage("plain")).buttons_json is None


def test_deliver_sends_and_marks_sent(db: Session, clock: FakeClock):
    _family(db)
    message = OutMessage("hi", (Button("New PIN", "new_pin:1"),))
    row = enqueue(db, message)
    db.commit()
    sender = FakeSender()
    assert asyncio.run(deliver_due(db, sender, clock)) == 1
    assert [(s.chat_id, s.message) for s in sender.sent] == [(555, message)]
    assert (row.status, row.attempts) == ("sent", 1)


def test_failure_keeps_message_queued_and_retries_later(db: Session, clock: FakeClock):
    _family(db)
    row = enqueue(db, OutMessage("hi"))
    db.commit()
    sender = FakeSender()
    sender.fail_next()
    assert asyncio.run(deliver_due(db, sender, clock)) == 0
    assert (row.status, row.attempts) == ("pending", 1)
    assert row.next_try_at == clock.now() + dt.timedelta(seconds=5)
    assert asyncio.run(deliver_due(db, sender, clock)) == 0
    assert sender.sent == []
    clock.advance(seconds=5)
    assert asyncio.run(deliver_due(db, sender, clock)) == 1
    assert row.status == "sent"
    assert row.attempts == 2


def test_failure_stops_the_pass_and_keeps_order(db: Session, clock: FakeClock):
    _family(db)
    enqueue(db, OutMessage("first"))
    enqueue(db, OutMessage("second"))
    db.commit()
    sender = FakeSender()
    sender.fail_next()
    asyncio.run(deliver_due(db, sender, clock))
    assert sender.sent == []
    clock.advance(seconds=5)
    assert asyncio.run(deliver_due(db, sender, clock)) == 2
    assert [s.message.text for s in sender.sent] == ["first", "second"]


def test_later_messages_wait_behind_a_pending_retry(db: Session, clock: FakeClock):
    _family(db)
    enqueue(db, OutMessage("first"))
    enqueue(db, OutMessage("second"))
    db.commit()
    sender = FakeSender()
    sender.fail_next()
    asyncio.run(deliver_due(db, sender, clock))
    clock.advance(seconds=2)  # mid-backoff poll
    assert asyncio.run(deliver_due(db, sender, clock)) == 0
    assert sender.sent == []
    clock.advance(seconds=3)
    assert asyncio.run(deliver_due(db, sender, clock)) == 2
    assert [s.message.text for s in sender.sent] == ["first", "second"]


def test_backoff_starts_when_the_send_fails(db: Session, clock: FakeClock):
    _family(db)
    row = enqueue(db, OutMessage("hi"))
    db.commit()

    class SlowFailingSender:
        async def send(self, chat_id: int, message: OutMessage) -> None:
            clock.advance(seconds=30)
            raise SendError("slow failure")

    asyncio.run(deliver_due(db, SlowFailingSender(), clock))
    assert row.next_try_at == clock.now() + dt.timedelta(seconds=5)


def test_backoff_grows_and_caps():
    assert [backoff_seconds(n) for n in range(1, 7)] == [5, 15, 60, 300, 900, 900]


def test_nothing_sent_without_linked_chat(db: Session, clock: FakeClock):
    _family(db, chat_id=None)
    row = enqueue(db, OutMessage("hi"))
    db.commit()
    sender = FakeSender()
    assert asyncio.run(deliver_due(db, sender, clock)) == 0
    assert (row.status, row.attempts) == ("pending", 0)
    assert sender.sent == []


def test_nothing_sent_without_family(db: Session, clock: FakeClock):
    enqueue(db, OutMessage("hi"))
    db.commit()
    assert asyncio.run(deliver_due(db, FakeSender(), clock)) == 0
    assert db.query(Outbox).one().status == "pending"
