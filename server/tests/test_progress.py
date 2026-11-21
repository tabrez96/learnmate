import datetime as dt

import pytest

from learnmate.plan import progress
from learnmate.plan.progress import (
    BADGES,
    best_streak,
    current_streak,
    earned_badges,
    level_for,
    streak_bonus,
)


def _jan(*days: int) -> list[dt.date]:
    return [dt.date(2026, 1, d) for d in days]


def test_point_values_match_s04() -> None:
    assert progress.test_points(5, double_points=False) == 100
    assert progress.test_points(7, double_points=False) == 100
    assert progress.test_points(3, double_points=False) == 60
    assert progress.test_points(5, double_points=True) == 200
    assert streak_bonus(3) == 30
    assert streak_bonus(9) == 50
    assert streak_bonus(0) == 0
    assert progress.WARMUP_POINTS == progress.QUICK_CHECK_POINTS == 10
    with pytest.raises(ValueError):
        progress.test_points(-1, double_points=False)


def test_levels_every_200_points() -> None:
    assert (level_for(0).number, level_for(0).title) == (1, "Newcomer")
    assert level_for(0).to_next == 200
    assert level_for(199).number == 1
    assert (level_for(200).number, level_for(200).title) == (2, "Starter")
    explorer = level_for(740)
    assert (explorer.number, explorer.title, explorer.next_title) == (
        4,
        "Explorer",
        "Scholar",
    )
    assert (explorer.floor, explorer.next_at, explorer.to_next) == (600, 800, 60)
    assert level_for(800).title == "Scholar"
    assert level_for(1000).title == "Expert"
    assert level_for(5000).title == "Master"
    assert level_for(-5).number == 1


def test_streak_counts_consecutive_days() -> None:
    days = _jan(3, 4, 5)
    assert current_streak(days, dt.date(2026, 1, 5)) == 3
    assert current_streak(days, dt.date(2026, 1, 6)) == 3
    assert current_streak(days, dt.date(2026, 1, 7)) == 0
    assert current_streak([], dt.date(2026, 1, 7)) == 0


def test_streak_ignores_duplicate_days() -> None:
    assert current_streak(_jan(4, 5, 5, 5), dt.date(2026, 1, 5)) == 2


def test_best_streak() -> None:
    assert best_streak(_jan(1, 2, 5, 6, 7, 8)) == 4
    assert best_streak([]) == 0


def test_badges() -> None:
    none = {"completed_sessions": 0, "best_streak": 0, "perfect_tests": 0, "points": 0}
    assert earned_badges(**none) == []
    assert earned_badges(**{**none, "completed_sessions": 1}) == ["first_session"]
    assert earned_badges(**{**none, "completed_sessions": 10}) == [
        "first_session",
        "sessions_10",
    ]
    assert "sessions_50" in earned_badges(**{**none, "completed_sessions": 50})
    assert earned_badges(**{**none, "best_streak": 7}) == ["streak_3", "streak_7"]
    assert "streak_30" in earned_badges(**{**none, "best_streak": 30})
    assert earned_badges(**{**none, "perfect_tests": 1}) == ["perfect_test"]
    assert earned_badges(**{**none, "points": 800}) == ["level_5"]
    everything = earned_badges(
        completed_sessions=50,
        best_streak=30,
        perfect_tests=1,
        points=900,
        completed_challenges=10,
    )
    assert everything == [badge_id for badge_id, _ in BADGES]


def test_challenge_badges() -> None:
    none = {"completed_sessions": 0, "best_streak": 0, "perfect_tests": 0, "points": 0}
    assert earned_badges(**none, completed_challenges=0) == []
    assert earned_badges(**none, completed_challenges=1) == ["first_challenge"]
    assert earned_badges(**none, completed_challenges=10) == [
        "first_challenge",
        "challenges_10",
    ]
