from learnmate.llm.types import BooksAnswer, Passage
from learnmate.mentor.answers import (
    answer_from_books,
    citations_ok,
    retrieval_record,
    source_lines,
)
from learnmate.rag.search import SearchHit

GOOD_VISUAL = {
    "kind": "steps",
    "caption": "c",
    "alt_text": "a",
    "steps": ["one", "two"],
}


def reply(ids=(1,), *, covered=True, text="Yes.", visual=None) -> BooksAnswer:
    return BooksAnswer(covered=covered, text=text, passage_ids=list(ids), visual=visual)


class Script:
    def __init__(self, *replies: BooksAnswer) -> None:
        self.replies = list(replies)
        self.calls = 0

    def __call__(self) -> BooksAnswer:
        self.calls += 1
        return self.replies.pop(0)


def test_citations_ok_rules() -> None:
    assert citations_ok(reply(), {1, 2})
    assert not citations_ok(reply([9]), {1})
    assert not citations_ok(reply([]), {1})
    assert not citations_ok(reply(text="  "), {1})
    assert not citations_ok(reply(covered=False), {1})


def test_answer_from_books_retries_bad_citation_then_not_covered() -> None:
    ask = Script(reply([9]), reply([8]))
    result = answer_from_books(ask, {1})
    assert result.answer is None
    assert result.attempts == 2
    assert ask.calls == 2


def test_answer_from_books_second_attempt_ok() -> None:
    ask = Script(reply([9]), reply([1]))
    result = answer_from_books(ask, {1})
    assert result.answer.passage_ids == [1]
    assert result.attempts == 2


def test_answer_from_books_not_covered_no_retry() -> None:
    ask = Script(reply([], covered=False, text=""))
    result = answer_from_books(ask, {1})
    assert (result.answer, result.attempts, ask.calls) == (None, 1, 1)


def test_answer_from_books_good_first_time_keeps_visual() -> None:
    ask = Script(reply(visual=GOOD_VISUAL))
    result = answer_from_books(ask, {1})
    assert result.visual["steps"] == ["one", "two"]
    assert ask.calls == 1


def test_answer_from_books_bad_visual_dropped() -> None:
    bad = {"kind": "steps", "steps": ["one", "two"]}  # no caption
    ask = Script(reply(visual=bad), reply(visual=bad))
    result = answer_from_books(ask, {1})
    assert result.answer is not None
    assert result.visual is None
    assert ask.calls == 2


def test_answer_from_books_bad_visual_then_bad_citation_keeps_first() -> None:
    bad = {"kind": "figure"}
    first = reply(text="First.", visual=bad)
    ask = Script(first, reply([9]))
    result = answer_from_books(ask, {1})
    assert result.answer is first
    assert result.visual is None


def test_source_lines_material_chapter_page() -> None:
    passages = {
        1: Passage(id=1, text="t", material="Plants", chapter="Roots", page=3),
        2: Passage(id=2, text="t", material="Maps", chapter="", page=None),
    }
    lines = source_lines([2, 1, 2], passages)
    assert lines == [
        {"passage_id": 2, "material": "Maps", "chapter": "", "page": None},
        {"passage_id": 1, "material": "Plants", "chapter": "Roots", "page": 3},
    ]


def test_retrieval_record_shape() -> None:
    hit = SearchHit(
        id=4,
        chunk_ids=[3, 4],
        material_id=1,
        chapter_id=None,
        page=1,
        text="t",
        score=0.5,
    )
    record = retrieval_record(
        mode="books", query="q", rerank=True, hits=[hit], covered=True, attempts=1
    )
    assert record["hits"] == [{"passage_id": 4, "chunk_ids": [3, 4], "score": 0.5}]
    assert record["query"] == "q"
    assert record["rerank"] is True


def test_answer_from_books_out_of_scope_figure_dropped() -> None:
    figure = {"kind": "figure", "caption": "c", "alt_text": "a", "figure_id": 9}
    ask = Script(reply(visual=figure), reply(visual=figure))
    result = answer_from_books(ask, {1}, {3})
    assert result.answer is not None
    assert result.visual is None
    assert ask.calls == 2


def test_answer_from_books_in_scope_figure_kept() -> None:
    figure = {"kind": "figure", "caption": "c", "alt_text": "a", "figure_id": 3}
    result = answer_from_books(Script(reply(visual=figure)), {1}, {3})
    assert result.visual["figure_id"] == 3
