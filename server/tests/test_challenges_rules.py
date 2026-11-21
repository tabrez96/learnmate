import pytest

from learnmate.challenges.rules import challenge_points, question_count


def test_question_counts() -> None:
    assert question_count("warmup") == 3
    assert question_count("challenge") == 1
    assert question_count("bonus") == 3
    with pytest.raises(ValueError):
        question_count("boss")


def test_challenge_points() -> None:
    assert challenge_points(0) == 0
    assert challenge_points(3) == 30
    with pytest.raises(ValueError):
        challenge_points(-1)
