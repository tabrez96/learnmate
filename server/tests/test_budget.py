import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from learnmate.clock import FakeClock
from learnmate.config import Settings
from learnmate.db import make_session_factory
from learnmate.llm import budget
from learnmate.llm.budget import (
    REACHED_MESSAGE,
    BudgetReached,
    cost_usd,
    month_bounds,
    record_usage,
    require_budget,
    status,
)
from learnmate.llm.fake import FakeLlm
from learnmate.llm.metered import MeteredLlm
from learnmate.llm.types import (
    LlmOutputError,
    LlmResult,
    Passage,
    Usage,
)
from learnmate.models import BudgetAlert, LlmUsage, Outbox
from learnmate.telegram import templates


def to_date(clock: FakeClock, target: dt.datetime) -> None:
    clock.advance(seconds=(target - clock.now()).total_seconds())


def spend(
    db: Session, settings: Settings, clock: FakeClock, output_tokens: int
) -> None:
    usage = Usage(settings.model_main, "lesson", 0, output_tokens)
    record_usage(db, settings, clock, usage)


def outbox_texts(db: Session) -> list[str]:
    return list(db.scalars(select(Outbox.text).order_by(Outbox.id)))


def metered(engine: Engine, settings: Settings, clock: FakeClock, inner) -> MeteredLlm:
    return MeteredLlm(inner, make_session_factory(engine, clock), settings, clock)


def test_cost_main_model(settings: Settings) -> None:
    usage = Usage(settings.model_main, "lesson", 100, 50)
    assert cost_usd(settings, usage) == Decimal("0.001050")


def test_cost_fast_model(settings: Settings) -> None:
    usage = Usage(settings.model_fast, "rewrite", 100, 50)
    assert cost_usd(settings, usage) == Decimal("0.000350")


def test_cost_web_search(settings: Settings) -> None:
    usage = Usage(settings.model_main, "outside", 100, 50, 1)
    assert cost_usd(settings, usage) == Decimal("0.011050")


def test_each_call_writes_usage_row(
    engine: Engine, db: Session, settings: Settings, clock: FakeClock
) -> None:
    llm = metered(engine, settings, clock, FakeLlm(settings))
    p = [Passage(id=1, text="t", material="m", chapter="c")]
    llm.read_page(b"x", "image/png")
    llm.detect_chapters(["p"])
    llm.rewrite_query("q", history=[])
    llm.build_lesson("t", passages=p, grade=6)
    llm.answer_from_passages("q", history=[], passages=p, grade=6)
    llm.answer_outside("q", history=[], grade=6)
    llm.generate_questions(passages=p, count=1, grade=6)
    llm.find_figures(b"x", "image/png")
    rows = db.scalars(select(LlmUsage).order_by(LlmUsage.id)).all()
    assert [r.purpose for r in rows] == [
        "read_page",
        "chapters",
        "rewrite",
        "lesson",
        "answer",
        "outside",
        "questions",
        "figures",
    ]
    for row in rows:
        searches = 1 if row.purpose == "outside" else 0
        usage = Usage(row.model, row.purpose, 100, 50, searches)  # type: ignore[arg-type]
        assert (row.input_tokens, row.output_tokens) == (100, 50)
        assert row.web_searches == searches
        assert row.cost_usd == cost_usd(settings, usage)
        assert row.at == clock.now()
    fast = {"read_page", "chapters", "rewrite", "figures"}
    assert all(
        r.model == (settings.model_fast if r.purpose in fast else settings.model_main)
        for r in rows
    )


def test_llm_error_usage_is_recorded(
    engine: Engine, db: Session, settings: Settings, clock: FakeClock
) -> None:
    class Failing:
        def build_lesson(self, *args: object, **kwargs: object) -> LlmResult:
            usage = Usage(settings.model_main, "lesson", 10, 5)
            raise LlmOutputError("x", usage)

    llm = metered(engine, settings, clock, Failing())
    with pytest.raises(LlmOutputError):
        llm.build_lesson("t", passages=[], grade=6)
    row = db.scalars(select(LlmUsage)).one()
    assert (row.input_tokens, row.output_tokens) == (10, 5)


def test_value_error_records_nothing(
    engine: Engine, db: Session, settings: Settings, clock: FakeClock
) -> None:
    llm = metered(engine, settings, clock, FakeLlm(settings))
    with pytest.raises(ValueError):
        llm.generate_questions(passages=[], count=1, grade=6)
    assert db.scalars(select(LlmUsage)).all() == []


def test_status_empty_month(db: Session, settings: Settings, clock: FakeClock) -> None:
    s = status(db, settings, clock)
    assert (s.spent_usd, s.budget_usd, s.reached) == (0, 10, False)


def test_status_sums_only_this_month(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    for at in (dt.datetime(2026, 1, 31, 23, 59), dt.datetime(2026, 2, 1, 0, 0)):
        db.add(
            LlmUsage(
                at=at,
                model=settings.model_main,
                purpose="lesson",
                cost_usd=Decimal("1.5"),
            )
        )
    db.commit()
    to_date(clock, dt.datetime(2026, 2, 10))
    s = status(db, settings, clock)
    assert s.month == "2026-02"
    assert s.spent_usd == Decimal("1.5")


def test_month_follows_timezone() -> None:
    month, start, _ = month_bounds(dt.datetime(2026, 1, 31, 19, 0), "Asia/Kolkata")
    assert month == "2026-02"
    assert start == dt.datetime(2026, 1, 31, 18, 30)


def test_month_bounds_december() -> None:
    month, start, end = month_bounds(dt.datetime(2026, 12, 15), "UTC")
    assert month == "2026-12"
    assert start == dt.datetime(2026, 12, 1)
    assert end == dt.datetime(2027, 1, 1)


def test_warning_alert_once_per_month(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    spend(db, settings, clock, 52_667)  # 0.79
    assert outbox_texts(db) == []
    spend(db, settings, clock, 1_000)  # 0.805
    warning = templates.budget_warning(80, 0.805, 1.0)
    assert outbox_texts(db) == [warning.text]
    spend(db, settings, clock, 6_667)  # 0.905
    assert len(outbox_texts(db)) == 1


def test_reached_alert_once_per_month(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    spend(db, settings, clock, 54_000)  # 0.81
    spend(db, settings, clock, 13_334)  # 1.010
    texts = outbox_texts(db)
    assert len(texts) == 2
    assert texts[1] == templates.budget_reached(1.01, 1.0).text
    spend(db, settings, clock, 1_000)
    assert len(outbox_texts(db)) == 2


def test_alerts_again_next_month(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    spend(db, settings, clock, 54_000)
    spend(db, settings, clock, 13_334)
    assert len(outbox_texts(db)) == 2
    to_date(clock, dt.datetime(2026, 2, 1, 9, 0))
    spend(db, settings, clock, 54_000)
    spend(db, settings, clock, 13_334)
    assert len(outbox_texts(db)) == 4
    months = set(db.scalars(select(BudgetAlert.month)))
    assert months == {"2026-01", "2026-02"}


def test_jump_past_both_sends_only_reached(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    spend(db, settings, clock, 80_000)  # 1.20
    assert outbox_texts(db) == [templates.budget_reached(1.2, 1.0).text]
    levels = set(db.scalars(select(BudgetAlert.level)))
    assert levels == {80, 100}


def test_budget_zero_is_reached_at_once(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 0})
    with pytest.raises(BudgetReached):
        require_budget(db, settings, clock)


def test_require_budget_raises_when_reached(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    spend(db, settings, clock, 60_000)  # 0.90
    assert require_budget(db, settings, clock).reached is False
    spend(db, settings, clock, 6_667)  # 1.000005
    with pytest.raises(BudgetReached) as info:
        require_budget(db, settings, clock)
    assert str(info.value) == REACHED_MESSAGE
    assert info.value.status.reached is True


def test_require_budget_raises_at_exact_budget(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 0.015})
    spend(db, settings, clock, 1_000)  # exactly 0.015
    with pytest.raises(BudgetReached):
        require_budget(db, settings, clock)


def test_require_budget_lifts_next_month(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    to_date(clock, dt.datetime(2026, 1, 31, 12, 0))
    spend(db, settings, clock, 80_000)
    with pytest.raises(BudgetReached):
        require_budget(db, settings, clock)
    to_date(clock, dt.datetime(2026, 2, 1, 0, 0))
    require_budget(db, settings, clock)


def test_require_budget_lifts_when_budget_raised(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    spend(db, settings, clock, 700_000)  # 10.50
    with pytest.raises(BudgetReached):
        require_budget(db, settings, clock)
    raised = settings.model_copy(update={"llm_monthly_budget_usd": 20})
    require_budget(db, raised, clock)
    spend(db, raised, clock, 1_000)
    assert len(outbox_texts(db)) == 1  # no second "reached" alert


def test_warning_at_exact_threshold(
    db: Session, settings: Settings, clock: FakeClock
) -> None:
    # 0.1 * 0.8 is 0.08000000000000002 in floats; Decimal keeps it exact.
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 0.1})
    record_usage(db, settings, clock, Usage(settings.model_fast, "rewrite", 80_000, 0))
    assert outbox_texts(db) == [templates.budget_warning(80, 0.08, 0.1).text]


def test_alert_conflict_before_enqueue_is_retried(
    db: Session,
    settings: Settings,
    clock: FakeClock,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = settings.model_copy(update={"llm_monthly_budget_usd": 1.0})
    real_enqueue = budget.enqueue
    raced = []

    def racing_enqueue(session: Session, message) -> None:
        if not raced:
            raced.append(True)
            with Session(engine) as other:
                other.add(BudgetAlert(month="2026-01", level=80))
                other.commit()
        real_enqueue(session, message)

    monkeypatch.setattr(budget, "enqueue", racing_enqueue)
    spend(db, settings, clock, 80_000)  # 1.20, jumps past both
    assert outbox_texts(db) == [templates.budget_reached(1.2, 1.0).text]
    assert set(db.scalars(select(BudgetAlert.level))) == {80, 100}
