"""Injected time. Naive UTC, to match the DateTime columns."""

import datetime as dt
from typing import Protocol


class Clock(Protocol):
    def now(self) -> dt.datetime: ...


class SystemClock:
    def now(self) -> dt.datetime:
        return dt.datetime.now(dt.UTC).replace(tzinfo=None)


class FakeClock:
    def __init__(self, start: dt.datetime = dt.datetime(2026, 1, 5, 9, 0)) -> None:
        self._now = start

    def now(self) -> dt.datetime:
        return self._now

    def advance(self, *, seconds: float) -> None:
        self._now += dt.timedelta(seconds=seconds)
