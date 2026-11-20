"""Every message the parent receives, as pure functions."""

import datetime as dt
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Button:
    text: str
    data: str  # callback data, e.g. "new_pin:12"


@dataclass(frozen=True)
class OutMessage:
    text: str
    buttons: tuple[Button, ...] = ()


@dataclass(frozen=True)
class SessionSummary:
    child: str
    subject: str
    studied_min: int
    score_pct: int | None  # None with missed=False: no graded test
    band: str | None
    missed: bool
    points: int
    left_count: int
    lock_minutes: tuple[int, ...]  # one entry per inactivity lock
    force_ended: bool


NEW_PIN_PREFIX = "new_pin:"
PinReason = Literal["new", "replaced", "resent"]

LINKED = "Connected. Learnmate will send session alerts and grades here."
LINK_REFUSED = (
    "That code didn't work. Make a new one in Learnmate's settings and try again."
)
NOT_LINKED = "This chat isn't connected to Learnmate."
NEW_PIN_UNAVAILABLE = "New PIN isn't available right now."
NEW_PIN_SENT = "New PIN sent."

_TEST_LABELS = {
    "daily": "the daily test",
    "weekly": "the weekly test",
    "surprise": "the surprise test",
    "test_only": "a test-only session",
}


def clock_time(at_utc: dt.datetime, tz: str) -> str:
    """Format a naive UTC time as HH:MM in the given IANA zone."""
    return at_utc.replace(tzinfo=dt.UTC).astimezone(ZoneInfo(tz)).strftime("%H:%M")


def _times(n: int) -> str:
    return "once" if n == 1 else f"{n} times"


def session_started(child: str, subject: str, time: str) -> OutMessage:
    return OutMessage(f"{child} started a {subject} session ({time}).")


def session_pin(child: str, pin: str, session_id: int, reason: PinReason) -> OutMessage:
    if reason == "new":
        text = (
            f"Session PIN for {child}'s session: {pin}. It works for this session only."
        )
    elif reason == "replaced":
        text = f"New session PIN for {child}'s session: {pin}. The old PIN no longer works."
    else:
        text = f"The session PIN again: {pin}. It's the same PIN as when the session started."
    return OutMessage(text, (Button("New PIN", f"{NEW_PIN_PREFIX}{session_id}"),))


def grade(
    child: str,
    kind: str,
    topic: str,
    score_pct: int,
    band: str,
    right: int,
    total: int,
    studied_min: int,
) -> OutMessage:
    if kind not in _TEST_LABELS:
        raise ValueError(f"no grade message for session kind {kind!r}")
    return OutMessage(
        f"{child} finished {_TEST_LABELS[kind]} on {topic}: {score_pct}% ({band}), "
        f"{right} of {total}. Studied {studied_min} min."
    )


def left_app(child: str, time: str) -> OutMessage:
    return OutMessage(f"{child} left Learnmate during the session ({time}).")


def back_in_app(child: str, time: str) -> OutMessage:
    return OutMessage(f"{child} is back ({time}).")


def locked(child: str, minutes: int, time: str) -> OutMessage:
    return OutMessage(
        f"{child}'s session locked after {minutes} minutes with no activity ({time})."
    )


def unlocked(child: str, time: str) -> OutMessage:
    return OutMessage(f"{child}'s session was unlocked ({time}).")


def pin_lockout(child: str, wrong: int, until: str) -> OutMessage:
    return OutMessage(
        f"{wrong} wrong PINs on {child}'s session. "
        f"The PIN pad is locked until {until}; the session keeps running."
    )


def fallback_lockout(child: str, wrong: int, until: str) -> OutMessage:
    return OutMessage(
        f"{wrong} wrong fallback passwords on {child}'s session. "
        f"The fallback password is locked until {until}."
    )


def force_ended(child: str, time: str) -> OutMessage:
    return OutMessage(
        f"{child}'s session was force-ended with the fallback password ({time})."
    )


def summary(s: SessionSummary) -> OutMessage:
    if s.missed:
        test = "Test: Missed"
    elif s.score_pct is None:
        test = "Test: none"
    else:
        test = f"Test: {s.score_pct}% ({s.band})"
    left = (
        "Left Learnmate: not once"
        if s.left_count == 0
        else (f"Left Learnmate: {_times(s.left_count)}")
    )
    lines = [
        f"Session summary: {s.child}, {s.subject}",
        f"Studied {s.studied_min} min",
        test,
        f"Points: +{s.points}",
        left,
    ]
    if s.lock_minutes:
        lines.append(
            f"Locked {_times(len(s.lock_minutes))} for no activity, "
            f"{sum(s.lock_minutes)} min"
        )
    if s.force_ended:
        lines.append("Force-ended with the fallback password")
    return OutMessage("\n".join(lines))


def budget_warning(percent: int, spent: float, budget: float) -> OutMessage:
    return OutMessage(
        f"AI spending this month is at {percent}% ({spent:.2f} of {budget:.2f} USD)."
    )


def budget_reached(spent: float, budget: float) -> OutMessage:
    return OutMessage(
        f"AI spending this month reached the budget ({spent:.2f} of {budget:.2f} USD). "
        "New lessons and material reading are paused until next month "
        "or until the budget is raised."
    )
