import copy
import datetime as dt

import pytest

from learnmate.plan.rules import (
    PlanError,
    PlanInput,
    build_plan,
    current_step,
    exam_in_window,
    set_step_status,
)

TODAY = dt.date(2026, 1, 5)


def _input(
    session_type: str = "learn",
    *,
    first_of_week: bool = False,
    exam_date: dt.date | None = None,
    topic: str | None = "Photosynthesis",
    question_count: int = 10,
) -> PlanInput:
    return PlanInput(session_type, question_count, topic, first_of_week, exam_date)


def _keys(plan: dict) -> list[str]:
    return [s["key"] for s in plan["steps"]]


def test_learn_plan_is_warmup_lesson_daily_test() -> None:
    plan = build_plan(_input())
    assert _keys(plan) == ["warmup", "lesson", "test"]
    warmup, lesson, test = plan["steps"]
    assert warmup["question_count"] == 3
    assert lesson["kind"] == "lesson" and lesson["topic"] == "Photosynthesis"
    assert test["kind"] == "daily" and test["question_count"] == 5
    assert plan["test_kind"] == "daily" and plan["exam_date"] is None
    assert {s["status"] for s in plan["steps"]} == {"pending"}


def test_recap_plan_names_the_chapter() -> None:
    plan = build_plan(_input("recap", topic="Fractions and decimals"))
    assert plan["steps"][1]["kind"] == "recap"
    assert plan["steps"][1]["topic"] == "Fractions and decimals"


def test_test_only_plan_skips_the_lesson() -> None:
    plan = build_plan(_input("test_only"))
    assert _keys(plan) == ["warmup", "test"]
    assert plan["steps"][1]["kind"] == "test_only"
    assert plan["steps"][1]["question_count"] == 10


def test_test_only_ignores_weekly_and_surprise() -> None:
    plan = build_plan(
        _input("test_only", first_of_week=True, exam_date=TODAY + dt.timedelta(days=2))
    )
    assert plan["test_kind"] == "test_only"
    assert plan["exam_date"] is None
    assert plan["steps"][-1]["double_points"] is False


def test_first_session_of_week_gets_weekly_test() -> None:
    plan = build_plan(_input(first_of_week=True))
    test = plan["steps"][-1]
    assert (test["kind"], test["question_count"], test["double_points"]) == (
        "weekly",
        15,
        False,
    )


def test_exam_window_gives_surprise_test() -> None:
    plan = build_plan(_input(exam_date=dt.date(2026, 1, 8)))
    test = plan["steps"][-1]
    assert (test["kind"], test["question_count"], test["double_points"]) == (
        "surprise",
        8,
        True,
    )
    assert plan["exam_date"] == "2026-01-08"


def test_surprise_beats_weekly() -> None:
    plan = build_plan(_input(first_of_week=True, exam_date=dt.date(2026, 1, 8)))
    assert plan["test_kind"] == "surprise"


def test_exam_in_window_bounds() -> None:
    day = dt.timedelta(days=1)
    assert exam_in_window(TODAY, [TODAY + day]) == TODAY + day
    assert exam_in_window(TODAY, [TODAY + 7 * day]) == TODAY + 7 * day
    assert exam_in_window(TODAY, [TODAY]) is None
    assert exam_in_window(TODAY, [TODAY + 8 * day]) is None
    assert exam_in_window(TODAY, [TODAY + 5 * day, TODAY + 2 * day]) == TODAY + 2 * day
    assert exam_in_window(TODAY, []) is None


@pytest.mark.parametrize("session_type", ["learn", "recap", "test_only"])
@pytest.mark.parametrize("first_of_week", [False, True])
@pytest.mark.parametrize("exam", [None, dt.date(2026, 1, 8)])
def test_test_is_always_last(
    session_type: str, first_of_week: bool, exam: dt.date | None
) -> None:
    plan = build_plan(_input(session_type, first_of_week=first_of_week, exam_date=exam))
    assert plan["steps"][-1]["key"] == "test"
    assert plan["steps"][-1]["kind"] == plan["test_kind"]
    assert _keys(plan).count("test") == 1


def test_test_step_cannot_be_skipped() -> None:
    with pytest.raises(PlanError) as e:
        set_step_status(build_plan(_input()), "test", "skipped")
    assert e.value.status == 422


def test_invalid_status_rejected() -> None:
    with pytest.raises(PlanError) as e:
        set_step_status(build_plan(_input()), "warmup", "pending")
    assert e.value.status == 422


def test_mark_steps_done_and_skipped() -> None:
    original = build_plan(_input())
    snapshot = copy.deepcopy(original)
    plan = original
    assert current_step(plan) == "warmup"
    plan = set_step_status(plan, "warmup", "skipped")
    assert original == snapshot
    assert current_step(plan) == "lesson"
    plan = set_step_status(plan, "lesson", "done")
    assert current_step(plan) == "test"
    plan = set_step_status(plan, "test", "done")
    assert current_step(plan) is None
    assert original == snapshot


def test_test_can_be_done_before_earlier_steps() -> None:
    plan = set_step_status(build_plan(_input()), "test", "done")
    assert current_step(plan) == "warmup"


def test_finished_step_cannot_change() -> None:
    plan = set_step_status(build_plan(_input()), "warmup", "done")
    with pytest.raises(PlanError) as e:
        set_step_status(plan, "warmup", "skipped")
    assert e.value.status == 409


def test_unknown_step() -> None:
    with pytest.raises(PlanError) as e:
        set_step_status(build_plan(_input()), "nope", "done")
    assert e.value.status == 404
