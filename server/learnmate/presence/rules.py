"""Presence rules: away or here, and when a silence counts as left. Pure: no database, no clock."""

import datetime as dt
from typing import Literal

PRESENCE_TYPES = ("left", "back", "heartbeat_lost")
Presence = Literal["here", "left", "lost"]


def presence(events: list[str]) -> Presence:
    """The last left/back/heartbeat_lost event in time order decides.

    None or 'back' is 'here'; 'left' is 'left' (the app said so); 'heartbeat_lost'
    is 'lost' (the watchdog said so).
    """
    state: Presence = "here"
    for type_ in events:
        if type_ == "left":
            state = "left"
        elif type_ == "heartbeat_lost":
            state = "lost"
        elif type_ == "back":
            state = "here"
    return state


def is_silent(last_beat: dt.datetime, now: dt.datetime, timeout_s: int) -> bool:
    return (now - last_beat).total_seconds() >= timeout_s


def lock_alert_minutes(lock_s: int) -> int:
    return max(1, lock_s // 60)
