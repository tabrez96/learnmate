"""Test rules: which questions to keep, scores and bands. Pure: no database, no clock."""

from dataclasses import dataclass

from learnmate.llm.types import Question
from learnmate.mentor.lesson import ChapterKey
from learnmate.plan.rules import TEST_STEP

GENERATE_ATTEMPTS = 3  # the first request plus two regenerations


class AssessError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class TestSpec:
    __test__ = False  # not a pytest class

    kind: str  # daily | weekly | surprise | test_only
    count: int
    double_points: bool


def test_spec(plan: dict) -> TestSpec:
    step = next((s for s in plan["steps"] if s["key"] == TEST_STEP), None)
    if step is None:
        raise AssessError(409, "This session has no test")
    return TestSpec(
        step["kind"], step["question_count"], step.get("double_points", False)
    )


# Not a test, despite the name.
test_spec.__test__ = False  # type: ignore[attr-defined]


def valid_questions(
    questions: list[Question], allowed_ids: set[int], seen_prompts: set[str]
) -> list[Question]:
    kept = []
    for q in questions:
        prompt = q.prompt.strip().lower()
        options = {o.strip().lower() for o in q.options}
        if q.passage_id not in allowed_ids or prompt in seen_prompts:
            continue
        if len(options) != len(q.options):
            continue
        seen_prompts.add(prompt)
        kept.append(q)
    return kept


def spread(
    questions: list[Question], chapter_of: dict[int, ChapterKey], count: int
) -> list[Question]:
    groups: dict[ChapterKey, list[Question]] = {}
    for q in questions:
        groups.setdefault(chapter_of[q.passage_id], []).append(q)
    queues = list(groups.values())
    chosen: list[Question] = []
    depth = 0
    while len(chosen) < count and any(depth < len(g) for g in queues):
        for g in queues:
            if depth < len(g) and len(chosen) < count:
                chosen.append(g[depth])
        depth += 1
    return chosen


def score_pct(right: int, total: int) -> int:
    if total <= 0 or not 0 <= right <= total:
        raise ValueError("need total > 0 and 0 <= right <= total")
    return (200 * right + total) // (2 * total)


def band_for(pct: int, bands: dict[str, int]) -> str:
    if not 0 <= pct <= 100:
        raise ValueError("pct must be between 0 and 100")
    return next(band for band, floor in bands.items() if floor <= pct)
