"""The plan for a session and the rules for marking its steps. Pure: no database, no clock."""

import copy
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass

WARMUP_QUESTIONS = 3
DAILY_QUESTIONS = 5
WEEKLY_QUESTIONS = 15
SURPRISE_QUESTIONS = 8
SURPRISE_WINDOW_DAYS = 7
STEP_STATUSES = ("pending", "done", "skipped")
TEST_STEP = "test"


class PlanError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class PlanInput:
    session_type: str
    question_count: int
    topic: str | None
    first_of_week: bool
    exam_date: dt.date | None


def exam_in_window(today: dt.date, exam_dates: Iterable[dt.date]) -> dt.date | None:
    """Earliest exam date d with today < d <= today + 7 days, else None."""
    last = today + dt.timedelta(days=SURPRISE_WINDOW_DAYS)
    inside = [d for d in exam_dates if today < d <= last]
    return min(inside) if inside else None


def _test_step(p: PlanInput) -> dict:
    if p.session_type == "test_only":
        kind, count, double = "test_only", p.question_count, False
    elif p.exam_date is not None:
        kind, count, double = "surprise", SURPRISE_QUESTIONS, True
    elif p.first_of_week:
        kind, count, double = "weekly", WEEKLY_QUESTIONS, False
    else:
        kind, count, double = "daily", DAILY_QUESTIONS, False
    return {
        "key": TEST_STEP,
        "kind": kind,
        "status": "pending",
        "question_count": count,
        "double_points": double,
    }


def build_plan(p: PlanInput) -> dict:
    steps: list[dict] = [
        {
            "key": "warmup",
            "kind": "warmup",
            "status": "pending",
            "question_count": WARMUP_QUESTIONS,
        }
    ]
    if p.session_type in ("learn", "recap"):
        kind = "lesson" if p.session_type == "learn" else "recap"
        steps.append(
            {"key": "lesson", "kind": kind, "status": "pending", "topic": p.topic}
        )
    test = _test_step(p)
    steps.append(test)
    surprise = test["kind"] == "surprise"
    return {
        "test_kind": test["kind"],
        "exam_date": p.exam_date.isoformat() if surprise and p.exam_date else None,
        "steps": steps,
    }


def current_step(plan: dict) -> str | None:
    for step in plan["steps"]:
        if step["status"] == "pending":
            return step["key"]
    return None


def set_step_status(plan: dict, key: str, status: str) -> dict:
    if status not in ("done", "skipped"):
        raise PlanError(422, "Status must be done or skipped")
    new = copy.deepcopy(plan)
    step = next((s for s in new["steps"] if s["key"] == key), None)
    if step is None:
        raise PlanError(404, "Step not found")
    if key == TEST_STEP and status == "skipped":
        raise PlanError(422, "The test can't be skipped")
    if step["status"] != "pending":
        raise PlanError(409, "Step already finished")
    step["status"] = status
    return new
