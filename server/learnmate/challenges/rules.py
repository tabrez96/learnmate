"""Challenge rules: kinds, sizes and points. Pure: no database, no clock."""

from learnmate.plan.progress import CHALLENGE_POINTS_PER_CORRECT
from learnmate.plan.rules import WARMUP_QUESTIONS

QUESTION_COUNTS = {"warmup": WARMUP_QUESTIONS, "challenge": 1, "bonus": 3}
KINDS = tuple(QUESTION_COUNTS)
RECENT_SESSIONS = 3  # earlier sessions whose chapters feed the challenges


def question_count(kind: str) -> int:
    try:
        return QUESTION_COUNTS[kind]
    except KeyError:
        raise ValueError(f"unknown challenge kind: {kind}") from None


def challenge_points(correct: int) -> int:
    if correct < 0:
        raise ValueError("correct must not be negative")
    return correct * CHALLENGE_POINTS_PER_CORRECT
