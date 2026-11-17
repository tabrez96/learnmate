import base64
import json
from types import SimpleNamespace

import pytest

from learnmate.config import Settings
from learnmate.llm.anthropic_llm import (
    _MAX_TOKENS,
    AnthropicLlm,
    _extract_json,
)
from learnmate.llm.types import (
    BooksAnswer,
    ChapterGuess,
    ChapterList,
    FigureList,
    Lesson,
    LessonStep,
    Llm,
    LlmOutputError,
    LlmUnavailableError,
    OutsideAnswer,
    PageText,
    Passage,
    Purpose,
    QuestionSet,
    QuickCheck,
    SearchQuery,
    Turn,
    model_for,
)
from learnmate.llm.types import Question as Q


class StubMessages:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class StubClient:
    def __init__(self, *replies):
        self.messages = StubMessages(replies)


def reply(text, *, tokens=(10, 5), searches=None):
    tool = None if searches is None else SimpleNamespace(web_search_requests=searches)
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=tokens[0], output_tokens=tokens[1], server_tool_use=tool
        ),
    )


def passage(i: int, page: int | None = None) -> Passage:
    return Passage(id=i, text=f"text {i}", material="Book", chapter="Ch 1", page=page)


CHECK = QuickCheck(
    prompt="p", options=["a", "b", "c", "d"], correct_index=0, explanation="e"
)
QUESTION = Q(
    prompt="p",
    options=["a", "b", "c", "d"],
    correct_index=1,
    explanation="e",
    passage_id=1,
)

CASES = [
    (
        "read_page",
        PageText,
        PageText(text="x"),
        lambda f: f.read_page(b"img", "image/png"),
    ),
    (
        "chapters",
        ChapterList,
        ChapterList(chapters=[ChapterGuess(name="n", start_page=1)]),
        lambda f: f.detect_chapters(["a", "b"], hint="H"),
    ),
    (
        "rewrite",
        SearchQuery,
        SearchQuery(query="q"),
        lambda f: f.rewrite_query("q", history=[]),
    ),
    (
        "lesson",
        Lesson,
        Lesson(steps=[LessonStep(title="t", body="b", check=CHECK, passage_ids=[1])]),
        lambda f: f.build_lesson("t", passages=[passage(1)], grade=6),
    ),
    (
        "answer",
        BooksAnswer,
        BooksAnswer(covered=True, text="t", passage_ids=[1]),
        lambda f: f.answer_from_passages(
            "q", history=[], passages=[passage(1)], grade=6
        ),
    ),
    (
        "outside",
        OutsideAnswer,
        OutsideAnswer(text="t", source_url="https://x.test"),
        lambda f: f.answer_outside("q", history=[], grade=6),
    ),
    (
        "questions",
        QuestionSet,
        QuestionSet(questions=[QUESTION]),
        lambda f: f.generate_questions(passages=[passage(1)], count=1, grade=6),
    ),
    (
        "figures",
        FigureList,
        FigureList(figures=[]),
        lambda f: f.find_figures(b"img", "image/png"),
    ),
]
CASE_PARAMS = pytest.mark.parametrize(("purpose", "output", "value", "call"), CASES)


def make(settings: Settings, *replies) -> tuple[AnthropicLlm, StubClient]:
    client = StubClient(*replies)
    return AnthropicLlm(client, settings), client


@CASE_PARAMS
def test_every_call_uses_the_right_model_and_returns_usage(
    settings: Settings, purpose: Purpose, output: type, value, call
) -> None:
    llm, client = make(settings, reply(value.model_dump_json()))
    result = call(llm)
    request = client.messages.requests[0]
    assert isinstance(result.value, output)
    assert result.usage.purpose == purpose
    assert result.usage.model == model_for(settings, purpose) == request["model"]
    expected = (
        settings.model_fast
        if purpose in {"read_page", "chapters", "rewrite", "figures"}
        else settings.model_main
    )
    assert request["model"] == expected
    assert request["max_tokens"] == _MAX_TOKENS[purpose]
    assert (result.usage.input_tokens, result.usage.output_tokens) == (10, 5)


@CASE_PARAMS
def test_only_outside_sends_web_search(
    settings: Settings, purpose: Purpose, output: type, value, call
) -> None:
    llm, client = make(settings, reply(value.model_dump_json()))
    call(llm)
    request = client.messages.requests[0]
    assert ("tools" in request) == (purpose == "outside")
    if purpose == "outside":
        assert request["tools"] == [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}
        ]


def outside_json() -> str:
    return OutsideAnswer(text="t", source_url="https://x.test").model_dump_json()


def test_text_blocks_are_joined_without_separator(settings: Settings) -> None:
    raw = OutsideAnswer(
        text="hello world", source_url="https://x.test"
    ).model_dump_json()
    cut = raw.index("hello") + 3
    response = reply(raw[:cut], searches=1)
    response.content = [
        SimpleNamespace(type="text", text=raw[:cut]),
        SimpleNamespace(type="web_search_tool_result", text="ignored"),
        SimpleNamespace(type="text", text=raw[cut:]),
    ]
    llm, client = make(settings, response)
    result = llm.answer_outside("q", history=[], grade=6)
    assert result.value.text == "hello world"
    assert len(client.messages.requests) == 1


def test_outside_counts_web_searches(settings: Settings) -> None:
    llm, _ = make(settings, reply(outside_json(), searches=2))
    assert llm.answer_outside("q", history=[], grade=6).usage.web_searches == 2


def test_retry_sums_web_searches(settings: Settings) -> None:
    llm, _ = make(settings, reply("bad", searches=1), reply(outside_json(), searches=1))
    assert llm.answer_outside("q", history=[], grade=6).usage.web_searches == 2


def test_non_text_blocks_are_ignored(settings: Settings) -> None:
    response = reply(outside_json())
    response.content.insert(0, SimpleNamespace(type="server_tool_use"))
    llm, _ = make(settings, response)
    assert llm.answer_outside("q", history=[], grade=6).value.text == "t"


def test_system_prompt_embeds_schema(settings: Settings) -> None:
    value = CASES[3][2]
    llm, client = make(settings, reply(value.model_dump_json()))
    llm.build_lesson("t", passages=[passage(1)], grade=6)
    assert (
        json.dumps(Lesson.model_json_schema()) in client.messages.requests[0]["system"]
    )


def test_extract_json_tolerates_fences_and_prose() -> None:
    body = PageText(text="x").model_dump_json()
    for text in (f"```json\n{body}\n```", f"Sure! {body} Hope that helps", body):
        assert PageText.model_validate_json(_extract_json(text)).text == "x"
    quoted = '{"text":"Use ```print(1)```"}'
    assert (
        PageText.model_validate_json(_extract_json(quoted)).text == "Use ```print(1)```"
    )


def test_invalid_json_retried_once_then_succeeds(settings: Settings) -> None:
    llm, client = make(
        settings, reply("not json"), reply(PageText(text="x").model_dump_json())
    )
    result = llm.read_page(b"img", "image/png")
    assert result.value.text == "x"
    assert len(client.messages.requests) == 2
    messages = client.messages.requests[1]["messages"]
    assert len(messages) == 3
    assert "not valid" in messages[-1]["content"]
    assert (result.usage.input_tokens, result.usage.output_tokens) == (20, 10)


def test_invalid_json_twice_raises_output_error(settings: Settings) -> None:
    llm, client = make(settings, reply("nope"), reply("still nope"))
    with pytest.raises(LlmOutputError) as info:
        llm.read_page(b"img", "image/png")
    assert (info.value.usage.input_tokens, info.value.usage.output_tokens) == (20, 10)
    assert len(client.messages.requests) == 2


def test_schema_violation_is_retried(settings: Settings) -> None:
    bad = json.loads(QuestionSet(questions=[QUESTION]).model_dump_json())
    bad["questions"][0]["options"] = ["a", "b", "c"]
    good = QuestionSet(questions=[QUESTION]).model_dump_json()
    llm, client = make(settings, reply(json.dumps(bad)), reply(good))
    result = llm.generate_questions(passages=[passage(1)], count=1, grade=6)
    assert len(result.value.questions) == 1
    assert len(client.messages.requests) == 2


def test_sdk_error_becomes_unavailable(settings: Settings) -> None:
    llm, _ = make(settings, RuntimeError("down"))
    with pytest.raises(LlmUnavailableError) as info:
        llm.read_page(b"img", "image/png")
    assert (info.value.usage.input_tokens, info.value.usage.output_tokens) == (0, 0)


def test_sdk_error_on_retry_keeps_first_usage(settings: Settings) -> None:
    llm, _ = make(settings, reply("bad"), RuntimeError())
    with pytest.raises(LlmUnavailableError) as info:
        llm.read_page(b"img", "image/png")
    assert (info.value.usage.input_tokens, info.value.usage.output_tokens) == (10, 5)


def test_image_calls_send_base64_image(settings: Settings) -> None:
    llm, client = make(
        settings,
        reply(PageText(text="x").model_dump_json()),
        reply(FigureList(figures=[]).model_dump_json()),
    )
    llm.read_page(b"img", "image/jpeg")
    llm.find_figures(b"img", "image/jpeg")
    for request in client.messages.requests:
        block = request["messages"][0]["content"][0]
        assert block["type"] == "image"
        assert block["source"]["media_type"] == "image/jpeg"
        assert block["source"]["data"] == base64.b64encode(b"img").decode()


def test_passages_and_history_rendered(settings: Settings) -> None:
    llm, client = make(settings, reply(CASES[4][2].model_dump_json()))
    llm.answer_from_passages(
        "q",
        history=[Turn(role="student", text="hi")],
        passages=[passage(7, page=3), passage(8)],
        grade=6,
    )
    text = client.messages.requests[0]["messages"][0]["content"]
    assert "[id 7] Book / Ch 1 / page 3\ntext 7" in text
    assert "[id 8] Book / Ch 1\ntext 8" in text
    assert "[id 8] Book / Ch 1 / page" not in text
    assert "student: hi" in text


def test_chapters_hint_and_page_markers(settings: Settings) -> None:
    llm, client = make(settings, reply(CASES[1][2].model_dump_json()))
    llm.detect_chapters(["a", "b"], hint="H")
    text = client.messages.requests[0]["messages"][0]["content"]
    assert text.startswith("Hint: H\n\n--- page 1 ---\na")
    assert "--- page 2 ---\nb" in text


def test_generate_questions_without_passages_raises(settings: Settings) -> None:
    llm, client = make(settings)
    with pytest.raises(ValueError):
        llm.generate_questions(passages=[], count=1, grade=6)
    assert client.messages.requests == []


def test_satisfies_protocol(settings: Settings) -> None:
    llm: Llm = AnthropicLlm(
        StubClient(reply(PageText(text="x").model_dump_json())), settings
    )
    assert llm.read_page(b"img", "image/png").value.text == "x"
