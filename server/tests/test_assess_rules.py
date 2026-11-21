import pytest

from learnmate.assess import rules
from learnmate.config import Settings
from learnmate.llm.types import Question
from learnmate.plan.rules import PlanInput, build_plan

BANDS = Settings().grade_bands


def _q(prompt: str = "What?", passage_id: int = 1, options=None) -> Question:
    return Question(
        prompt=prompt,
        options=options or ["a", "b", "c", "d"],
        correct_index=0,
        explanation="Because.",
        passage_id=passage_id,
    )


@pytest.mark.parametrize(
    ("pct", "band"),
    [
        (100, "A"),
        (90, "A"),
        (89, "B"),
        (80, "B"),
        (79, "C"),
        (70, "C"),
        (69, "D"),
        (60, "D"),
        (59, "E"),
        (50, "E"),
        (49, "F"),
        (0, "F"),
    ],
)
def test_band_boundaries(pct: int, band: str) -> None:
    assert rules.band_for(pct, BANDS) == band


@pytest.mark.parametrize("pct", [-1, 101])
def test_band_rejects_out_of_range(pct: int) -> None:
    with pytest.raises(ValueError):
        rules.band_for(pct, BANDS)


@pytest.mark.parametrize(
    ("right", "total", "pct"),
    [(2, 3, 67), (1, 3, 33), (1, 8, 13), (4, 5, 80), (0, 5, 0), (5, 5, 100)],
)
def test_score_pct_rounds_half_up(right: int, total: int, pct: int) -> None:
    assert rules.score_pct(right, total) == pct


@pytest.mark.parametrize(("right", "total"), [(0, 0), (6, 5), (-1, 5)])
def test_score_pct_rejects_bad_input(right: int, total: int) -> None:
    with pytest.raises(ValueError):
        rules.score_pct(right, total)


def test_valid_questions_drops_unknown_passage_ids() -> None:
    kept = rules.valid_questions([_q("A?", 1), _q("B?", 99)], {1, 2}, set())
    assert [q.prompt for q in kept] == ["A?"]


def test_valid_questions_drops_duplicate_prompts_and_options() -> None:
    seen = {"old?"}
    questions = [
        _q("New?"),
        _q(" new? "),
        _q("Old?"),
        _q("Same options?", options=["a", "A ", "c", "d"]),
    ]
    kept = rules.valid_questions(questions, {1}, seen)
    assert [q.prompt for q in kept] == ["New?"]
    assert "new?" in seen


def test_spread_takes_round_robin_across_chapters() -> None:
    x, y = (1, 10), (1, 11)
    questions = [_q(f"X{i}", 1) for i in range(6)] + [_q(f"Y{i}", 2) for i in range(2)]
    chosen = rules.spread(questions, {1: x, 2: y}, 5)
    assert [q.prompt for q in chosen] == ["X0", "Y0", "X1", "Y1", "X2"]


def test_spread_returns_fewer_when_short() -> None:
    assert len(rules.spread([_q("A")], {1: (1, None)}, 5)) == 1


def _plan() -> dict:
    return build_plan(PlanInput("learn", 5, "Roots", False, None))


def test_test_spec_reads_the_plan_step() -> None:
    spec = rules.test_spec(_plan())
    assert (spec.kind, spec.count, spec.double_points) == ("daily", 5, False)


def test_test_spec_missing_step_raises_409() -> None:
    plan = {"steps": [s for s in _plan()["steps"] if s["key"] != "test"]}
    with pytest.raises(rules.AssessError) as e:
        rules.test_spec(plan)
    assert e.value.status == 409
