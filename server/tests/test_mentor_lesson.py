import pytest

from learnmate.llm.types import Lesson, LessonStep, Passage, QuickCheck
from learnmate.mentor.lesson import (
    MentorError,
    ScopeChunk,
    answer_check,
    citations_valid,
    group_by_chapter,
    heading_of,
    lesson_entry,
    select_passages,
    with_lesson,
)


def _chunk(
    id: int, text: str, *, chapter_id: int | None = 1, chapter: str = "Roots"
) -> ScopeChunk:
    return ScopeChunk(
        id=id,
        material_id=1,
        chapter_id=chapter_id,
        material="Plants",
        chapter=chapter,
        page=id,
        position=id,
        text=text,
    )


class Recorder:
    def __init__(self, answers: dict[str, list[int]] | None = None) -> None:
        self.answers = answers or {}
        self.queries: list[str] = []

    def __call__(self, key: tuple[int, int | None], query: str) -> list[int]:
        self.queries.append(query)
        return self.answers.get(query, [])


def _lesson(*ids: list[int]) -> Lesson:
    check = QuickCheck(
        prompt="Which?", options=["A", "B", "C", "D"], correct_index=2, explanation="C."
    )
    return Lesson(
        steps=[
            LessonStep(title=f"Step {n}", body="Body.", check=check, passage_ids=i)
            for n, i in enumerate(ids)
        ]
    )


def _plan(with_lesson_entry: dict | None = None) -> dict:
    lesson = {"key": "lesson", "kind": "lesson", "status": "pending", "topic": "Roots"}
    plan = {
        "steps": [
            {"key": "warmup", "status": "pending"},
            lesson,
            {"key": "test", "status": "pending"},
        ]
    }
    return with_lesson(plan, with_lesson_entry) if with_lesson_entry else plan


def test_heading_of() -> None:
    assert heading_of("Roots\nRoots hold the plant.") == "Roots"
    assert heading_of("Plants make food.\nMore") is None
    assert heading_of("Roots only") is None
    assert heading_of("Roots\n  ") is None
    assert heading_of(("x" * 81) + "\nBody") is None


def test_group_by_chapter() -> None:
    chunks = [_chunk(1, "a"), _chunk(2, "b"), _chunk(3, "c", chapter_id=2)]
    assert [[c.id for c in g] for g in group_by_chapter(chunks)] == [[1, 2], [3]]
    assert group_by_chapter([]) == []


def test_short_chapters_keep_everything_in_order() -> None:
    chunks = [
        _chunk(1, "aa"),
        _chunk(2, "bb"),
        _chunk(3, "cc", chapter_id=2, chapter="Leaves"),
    ]
    retrieve = Recorder()
    passages = select_passages(chunks, retrieve, max_chars=1000)
    assert [p.id for p in passages] == [1, 2, 3]
    assert retrieve.queries == []
    assert passages[2].chapter == "Leaves"


def test_long_chapter_uses_heading_passages() -> None:
    chunks = [_chunk(i, f"Head{i}\n" + "x" * 90) for i in range(1, 7)]
    retrieve = Recorder({"Head5": [5], "Roots": [3, 99], "Head2": [2]})
    passages = select_passages(chunks, retrieve, max_chars=300)
    ids = [p.id for p in passages]
    assert ids == [2, 3, 5]  # priority passages, in reading order
    assert sum(len(p.text) for p in passages) <= 300
    assert retrieve.queries == ["Roots"] + [f"Head{i}" for i in range(1, 7)]


def test_long_chapter_falls_back_to_reading_order() -> None:
    chunks = [_chunk(i, "x" * 100) for i in range(1, 6)]
    passages = select_passages(chunks, Recorder(), max_chars=250)
    assert [p.id for p in passages] == [1, 2]


def test_first_chunk_always_kept() -> None:
    passages = select_passages([_chunk(1, "x" * 500), _chunk(2, "y")], Recorder(), 100)
    assert [p.id for p in passages] == [1]


def test_share_split_across_chapters() -> None:
    chunks = [
        _chunk(c * 10 + i, "x" * 200, chapter_id=c, chapter=f"C{c}")
        for c in (1, 2, 3)
        for i in range(1, 8)
    ]
    passages = select_passages(chunks, Recorder(), max_chars=3000)
    for c in (1, 2, 3):
        assert sum(len(p.text) for p in passages if p.chapter == f"C{c}") <= 1000


def test_select_passages_empty() -> None:
    assert select_passages([], Recorder()) == []


def test_citations_valid() -> None:
    assert citations_valid(_lesson([1], [1, 2]), {1, 2})
    assert not citations_valid(_lesson([1], [3]), {1, 2})
    assert not citations_valid(_lesson([1], []), {1, 2})


def test_lesson_entry_sources() -> None:
    passages = [
        Passage(id=1, text="t", material="Plants", chapter="Roots", page=4),
        Passage(id=2, text="u", material="Plants", chapter="Leaves"),
    ]
    entry = lesson_entry(_lesson([1, 2]), passages)
    step = entry["steps"][0]
    assert step["sources"] == [
        {"passage_id": 1, "material": "Plants", "chapter": "Roots", "page": 4},
        {"passage_id": 2, "material": "Plants", "chapter": "Leaves", "page": None},
    ]
    assert step["answer_index"] is None
    assert step["check"]["correct_index"] == 2


def test_answer_check() -> None:
    passages = [Passage(id=1, text="t", material="M", chapter="C")]
    plan = _plan(lesson_entry(_lesson([1], [1]), passages))
    new, correct = answer_check(plan, 0, 2)
    assert correct
    assert new["steps"][1]["lesson"]["steps"][0]["answer_index"] == 2
    assert plan["steps"][1]["lesson"]["steps"][0]["answer_index"] is None
    _, correct = answer_check(plan, 1, 0)
    assert not correct
    with pytest.raises(MentorError) as again:
        answer_check(new, 0, 1)
    assert again.value.status == 409
    for bad in (2, -1):
        with pytest.raises(MentorError) as missing:
            answer_check(plan, bad, 0)
        assert missing.value.status == 404


def test_answer_check_without_lesson() -> None:
    with pytest.raises(MentorError) as e:
        answer_check(_plan(), 0, 0)
    assert e.value.status == 409
    with pytest.raises(MentorError) as e:
        answer_check({"steps": [{"key": "test"}]}, 0, 0)
    assert e.value.detail == "This session has no lesson"
