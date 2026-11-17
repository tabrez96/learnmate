"""The monthly AI budget: price and record every call, alert at 80% and 100%, refuse new work once reached."""

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.types import Usage
from learnmate.models import BudgetAlert, LlmUsage
from learnmate.telegram import templates
from learnmate.telegram.outbox import enqueue

_MILLION = Decimal(1_000_000)
_MICRO = Decimal("0.000001")
REACHED_MESSAGE = (
    "This month's AI budget has been used up, so new lessons and material reading "
    "are paused until the 1st of next month or until a parent raises the budget."
)


def _dec(x: float) -> Decimal:
    return Decimal(str(x))


def cost_usd(settings: Settings, usage: Usage) -> Decimal:
    price = settings.llm_prices[usage.model]
    tokens = (
        usage.input_tokens * _dec(price.input)
        + usage.output_tokens * _dec(price.output)
    ) / _MILLION
    searches = usage.web_searches * _dec(settings.llm_web_search_usd)
    return (tokens + searches).quantize(_MICRO, ROUND_HALF_UP)


def month_bounds(now: dt.datetime, tz: str) -> tuple[str, dt.datetime, dt.datetime]:
    """The family's calendar month around naive UTC `now`: label, start and end as naive UTC."""
    zone = ZoneInfo(tz)
    local = now.replace(tzinfo=dt.UTC).astimezone(zone)
    start = dt.datetime(local.year, local.month, 1, tzinfo=zone)
    if local.month == 12:
        end = dt.datetime(local.year + 1, 1, 1, tzinfo=zone)
    else:
        end = dt.datetime(local.year, local.month + 1, 1, tzinfo=zone)

    def to_utc(value: dt.datetime) -> dt.datetime:
        return value.astimezone(dt.UTC).replace(tzinfo=None)

    return f"{local.year:04d}-{local.month:02d}", to_utc(start), to_utc(end)


@dataclass(frozen=True)
class BudgetStatus:
    month: str  # YYYY-MM, local
    spent_usd: Decimal
    budget_usd: Decimal
    reached: bool


def status(db: Session, settings: Settings, clock: Clock) -> BudgetStatus:
    month, start, end = month_bounds(clock.now(), settings.timezone)
    total = db.scalar(
        select(func.sum(LlmUsage.cost_usd)).where(
            LlmUsage.at >= start, LlmUsage.at < end
        )
    )
    spent = (Decimal(str(total)) if total is not None else Decimal(0)).quantize(_MICRO)
    budget = _dec(settings.llm_monthly_budget_usd)
    return BudgetStatus(month, spent, budget, spent >= budget)


class BudgetReached(Exception):
    def __init__(self, status: BudgetStatus) -> None:
        super().__init__(REACHED_MESSAGE)
        self.status = status


def require_budget(db: Session, settings: Settings, clock: Clock) -> BudgetStatus:
    """Call before starting a session, a lesson or material reading."""
    current = status(db, settings, clock)
    if current.reached:
        raise BudgetReached(current)
    return current


def record_usage(
    db: Session, settings: Settings, clock: Clock, usage: Usage
) -> LlmUsage:
    # Commits on purpose: the spend must be kept even if the caller later rolls back.
    row = LlmUsage(
        at=clock.now(),
        model=usage.model,
        purpose=usage.purpose,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        web_searches=usage.web_searches,
        cost_usd=cost_usd(settings, usage),
    )
    db.add(row)
    db.commit()
    check_alerts(db, settings, clock)
    return row


def check_alerts(db: Session, settings: Settings, clock: Clock) -> None:
    for _ in range(2):
        try:
            _queue_alert(db, settings, clock)
            return
        except IntegrityError:
            # Another call recorded the same alert first: decide again with fresh markers.
            db.rollback()


def _queue_alert(db: Session, settings: Settings, clock: Clock) -> None:
    current = status(db, settings, clock)
    sent = set(
        db.scalars(select(BudgetAlert.level).where(BudgetAlert.month == current.month))
    )
    budget = float(current.budget_usd)
    spent = float(current.spent_usd)
    if current.reached:
        if 100 in sent:
            return
        if 80 not in sent:
            # Passed both at once: only the 100% message.
            db.add(BudgetAlert(month=current.month, level=80))
        db.add(BudgetAlert(month=current.month, level=100))
        enqueue(db, templates.budget_reached(spent, budget))
    elif (
        current.spent_usd
        >= current.budget_usd * _dec(settings.llm_budget_alert_fraction)
        and 80 not in sent
    ):
        db.add(BudgetAlert(month=current.month, level=80))
        percent = round(settings.llm_budget_alert_fraction * 100)
        enqueue(db, templates.budget_warning(percent, spent, budget))
    else:
        return
    db.commit()
