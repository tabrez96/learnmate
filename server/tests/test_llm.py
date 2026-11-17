import ast
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from learnmate.config import Settings
from learnmate.llm import make_llm
from learnmate.llm.anthropic_llm import AnthropicLlm
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import (
    FAST_PURPOSES,
    BooksAnswer,
    ChapterGuess,
    ChapterList,
    FigureList,
    Lesson,
    Llm,
    LlmError,
    LlmOutputError,
    LlmResult,
    LlmUnavailableError,
    OutsideAnswer,
    PageText,
    Passage,
    Purpose,
    QuestionSet,
    QuickCheck,
    SearchQuery,
    Usage,
    model_for,
)
from learnmate.main import create_app

PACKAGE = Path(__file__).resolve().parent.parent / "learnmate"
PURPOSES: list[Purpose] = list(get_args(Purpose.__value__))


def passage(i: int) -> Passage:
    return Passage(id=i, text="t", material="m", chapter="c")


def test_usage_add_sums_counters() -> None:
    total = Usage("m", "lesson", 10, 5, 1) + Usage("m", "lesson", 20, 10, 2)
    assert total == Usage("m", "lesson", 30, 15, 3)


def test_usage_add_rejects_mismatch() -> None:
    with pytest.raises(ValueError):
        Usage("m", "lesson") + Usage("m", "answer")
    with pytest.raises(ValueError):
        Usage("m", "lesson") + Usage("n", "lesson")


def test_errors_carry_usage() -> None:
    u = Usage("m", "lesson")
    for cls in (LlmOutputError, LlmUnavailableError):
        err = cls("x", u)
        assert isinstance(err, LlmError)
        assert err.usage is u
        assert str(err) == "x"


@pytest.mark.parametrize("purpose", PURPOSES)
def test_model_for_purposes(settings: Settings, purpose: Purpose) -> None:
    expected = settings.model_fast if purpose in FAST_PURPOSES else settings.model_main
    assert model_for(settings, purpose) == expected


def test_output_models_validate() -> None:
    with pytest.raises(ValidationError):
        QuickCheck(
            prompt="p", options=["a", "b", "c"], correct_index=0, explanation="e"
        )
    with pytest.raises(ValidationError):
        ChapterGuess(name="n", start_page=0)
    with pytest.raises(ValidationError):
        Lesson(steps=[])
    assert FigureList(figures=[]).figures == []


def test_fake_selected_in_tests(settings: Settings) -> None:
    assert isinstance(create_app(settings).state.llm, FakeLlm)
    assert isinstance(make_llm(Settings()), FakeLlm)


def test_make_llm_anthropic() -> None:
    llm = make_llm(Settings(llm_provider="anthropic", anthropic_api_key="test-key"))
    assert isinstance(llm, AnthropicLlm)


@pytest.mark.parametrize(
    ("purpose", "output", "call"),
    [
        ("read_page", PageText, lambda f: f.read_page(b"x", "image/png")),
        ("chapters", ChapterList, lambda f: f.detect_chapters(["p"], hint="H")),
        ("rewrite", SearchQuery, lambda f: f.rewrite_query("q", history=[])),
        (
            "lesson",
            Lesson,
            lambda f: f.build_lesson("t", passages=[passage(1)], grade=6),
        ),
        (
            "answer",
            BooksAnswer,
            lambda f: f.answer_from_passages(
                "q", history=[], passages=[passage(1)], grade=6
            ),
        ),
        (
            "outside",
            OutsideAnswer,
            lambda f: f.answer_outside("q", history=[], grade=6),
        ),
        (
            "questions",
            QuestionSet,
            lambda f: f.generate_questions(passages=[passage(1)], count=1, grade=6),
        ),
        ("figures", FigureList, lambda f: f.find_figures(b"x", "image/png")),
    ],
)
def test_fake_every_call_returns_result_with_usage(
    settings: Settings, purpose: Purpose, output: type, call
) -> None:
    result = call(FakeLlm(settings))
    assert isinstance(result, LlmResult)
    assert isinstance(result.value, output)
    assert result.usage.purpose == purpose
    assert result.usage.model == model_for(settings, purpose)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (100, 50)


def test_fake_questions_and_outside(settings: Settings) -> None:
    fake = FakeLlm(settings)
    qs = fake.generate_questions(passages=[passage(1), passage(2)], count=3, grade=6)
    assert [q.passage_id for q in qs.value.questions] == [1, 2, 1]
    with pytest.raises(ValueError):
        fake.generate_questions(passages=[], count=1, grade=6)
    assert fake.answer_outside("q", history=[], grade=6).usage.web_searches == 1
    assert fake.calls == ["questions", "outside"]


def test_fake_answer_without_passages(settings: Settings) -> None:
    answer = (
        FakeLlm(settings)
        .answer_from_passages("q", history=[], passages=[], grade=6)
        .value
    )
    assert answer.covered is False
    assert answer.text == ""
    assert answer.passage_ids == []


def test_fake_satisfies_protocol(settings: Settings) -> None:
    llm: Llm = FakeLlm(settings)
    assert llm.read_page(b"x", "image/png").usage.purpose == "read_page"


def test_only_llm_imports_anthropic() -> None:
    for path in PACKAGE.rglob("*.py"):
        if "llm" in path.relative_to(PACKAGE).parts[:1]:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(n.split(".")[0] == "anthropic" for n in names), path


def test_model_ids_only_in_settings() -> None:
    for path in PACKAGE.rglob("*.py"):
        if path.name != "config.py":
            assert "claude-" not in path.read_text(), path
