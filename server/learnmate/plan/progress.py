"""Points values, levels, streaks and badges. Pure: levels, streaks and badges are derived."""

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass

WARMUP_POINTS = 10
CHALLENGE_POINTS_PER_CORRECT = 10
QUICK_CHECK_POINTS = 10
TEST_POINTS_PER_CORRECT = 20
TEST_POINTS_MAX = 100
STREAK_POINTS_PER_DAY = 10
STREAK_POINTS_MAX = 50
LEVEL_POINTS = 200
# Level 1 is 0-199 points, so the spec's Starter..Expert are levels 2-6.
LEVEL_TITLES = (
    "Newcomer",
    "Starter",
    "Learner",
    "Explorer",
    "Scholar",
    "Expert",
    "Master",
)

BADGES = (
    ("first_session", "First session"),
    ("sessions_10", "10 sessions"),
    ("sessions_50", "50 sessions"),
    ("streak_3", "3-day streak"),
    ("streak_7", "7-day streak"),
    ("streak_30", "30-day streak"),
    ("perfect_test", "Perfect test"),
    ("level_5", "Scholar"),
    ("first_challenge", "First challenge"),
    ("challenges_10", "10 challenges"),
)


def test_points(correct: int, *, double_points: bool) -> int:
    if correct < 0:
        raise ValueError("correct must not be negative")
    points = min(correct * TEST_POINTS_PER_CORRECT, TEST_POINTS_MAX)
    return points * 2 if double_points else points


# Not a test, despite the name.
test_points.__test__ = False  # type: ignore[attr-defined]


def streak_bonus(streak_days: int) -> int:
    if streak_days <= 0:
        return 0
    return min(streak_days * STREAK_POINTS_PER_DAY, STREAK_POINTS_MAX)


@dataclass(frozen=True)
class Level:
    number: int
    title: str
    next_title: str
    floor: int
    next_at: int
    to_next: int


def _title(number: int) -> str:
    return LEVEL_TITLES[min(number, len(LEVEL_TITLES)) - 1]


def level_for(points: int) -> Level:
    points = max(points, 0)
    number = points // LEVEL_POINTS + 1
    next_at = number * LEVEL_POINTS
    return Level(
        number=number,
        title=_title(number),
        next_title=_title(number + 1),
        floor=(number - 1) * LEVEL_POINTS,
        next_at=next_at,
        to_next=next_at - points,
    )


def current_streak(days: Iterable[dt.date], today: dt.date) -> int:
    seen = set(days)
    day = today if today in seen else today - dt.timedelta(days=1)
    count = 0
    while day in seen:
        count += 1
        day -= dt.timedelta(days=1)
    return count


def best_streak(days: Iterable[dt.date]) -> int:
    best = run = 0
    previous: dt.date | None = None
    for day in sorted(set(days)):
        run = run + 1 if previous and day - previous == dt.timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


def earned_badges(
    *,
    completed_sessions: int,
    best_streak: int,
    perfect_tests: int,
    points: int,
    completed_challenges: int = 0,
) -> list[str]:
    met = {
        "first_session": completed_sessions >= 1,
        "sessions_10": completed_sessions >= 10,
        "sessions_50": completed_sessions >= 50,
        "streak_3": best_streak >= 3,
        "streak_7": best_streak >= 7,
        "streak_30": best_streak >= 30,
        "perfect_test": perfect_tests >= 1,
        "level_5": level_for(points).number >= 5,
        "first_challenge": completed_challenges >= 1,
        "challenges_10": completed_challenges >= 10,
    }
    return [badge_id for badge_id, _ in BADGES if met[badge_id]]
