"""The real provider: the Anthropic Messages API with JSON output validated by pydantic."""

import base64
import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from learnmate.config import Settings
from learnmate.llm.types import (
    BooksAnswer,
    ChapterList,
    FigureList,
    Lesson,
    LlmOutputError,
    LlmResult,
    LlmUnavailableError,
    OutsideAnswer,
    PageText,
    Passage,
    Purpose,
    QuestionSet,
    SearchQuery,
    Turn,
    Usage,
    model_for,
)


def make_client(api_key: str) -> Any:
    import anthropic  # the only import of the SDK; kept local so tests never load it

    return anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=120.0)


_MAX_TOKENS: dict[Purpose, int] = {
    "read_page": 4096,
    "chapters": 2048,
    "rewrite": 256,
    "lesson": 8192,
    "answer": 2048,
    "outside": 2048,
    "questions": 8192,
    "figures": 1024,
}
_WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

_PROMPTS: dict[Purpose, str] = {
    "read_page": (
        "You read one page of a student's school material from an image. Transcribe "
        "all of its text in reading order, keeping headings and lists. Describe each "
        "diagram in one line in square brackets. Do not add anything that is not on "
        "the page."
    ),
    "chapters": (
        "You get the pages of one school document, each marked with its page number. "
        "List the chapters it contains with the page each one starts on, in order. "
        "If a hint is given, use it for the chapter names. If there are no clear "
        "chapters, return one chapter for the whole document starting on page 1."
    ),
    "rewrite": (
        "Rewrite the student's latest question as one standalone search query for "
        "their school notes, using the conversation to resolve words like 'it' or "
        "'that'. Keep key terms exactly as written."
    ),
    "lesson": (
        "You are a patient tutor. Teach the topic to a student of the given school "
        "grade in short steps, using only the passages. Each step has a title, a "
        "body of a few sentences, one multiple-choice quick check with four options, "
        "and the ids of the passages it is based on."
    ),
    "answer": (
        "You are a patient tutor answering a student of the given school grade. "
        "Answer only from the passages and list the ids you used. If the passages do "
        "not answer the question, set covered to false, leave text empty and "
        "passage_ids empty. Use visual only for a simple chart or table that helps, "
        "otherwise null."
    ),
    "outside": (
        "You are a patient tutor answering a student of the given school grade. The "
        "student's notes did not cover this question, so search the web, prefer "
        "educational sources, answer in a few sentences at the student's level, and "
        "put the URL of the main source in source_url. Use visual only for a simple "
        "chart or table that helps, otherwise null."
    ),
    "questions": (
        "Write exactly the requested number of multiple-choice test questions for a "
        "student of the given school grade, using only the passages. Each has four "
        "options, the index of the correct one, a one-sentence explanation and the "
        "id of the passage it is based on. Spread the questions over the passages."
    ),
    "figures": (
        "Find each figure, diagram, chart or photo on this page image. For each give "
        "a one-line description and its bounding box as x0, y0, x1, y1 fractions of "
        "the page width and height (0 to 1)."
    ),
}


def _system(purpose: Purpose, output: type[BaseModel]) -> str:
    schema = json.dumps(output.model_json_schema())
    return (
        f"{_PROMPTS[purpose]}\n\nReply with only one JSON object that matches this "
        f"JSON schema, with no other text:\n{schema}"
    )


def _passages(passages: list[Passage]) -> str:
    blocks = []
    for p in passages:
        page = f" / page {p.page}" if p.page is not None else ""
        blocks.append(f"[id {p.id}] {p.material} / {p.chapter}{page}\n{p.text}")
    return "\n\n".join(blocks)


def _history(history: list[Turn]) -> str:
    if not history:
        return "Conversation so far: (none)"
    lines = "\n".join(f"{t.role}: {t.text}" for t in history)
    return f"Conversation so far:\n{lines}"


def _image(image: bytes, media_type: str) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(image).decode(),
        },
    }


def _extract_json(text: str) -> str:
    # A reply that starts with an object is not fenced; a fence inside its strings must stay.
    fenced = None if text.lstrip().startswith("{") else _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text.strip()


def _usage(model: str, purpose: Purpose, response: Any) -> Usage:
    u = response.usage
    tools = getattr(u, "server_tool_use", None)
    searches = (getattr(tools, "web_search_requests", 0) or 0) if tools else 0
    return Usage(model, purpose, u.input_tokens, u.output_tokens, searches)


class AnthropicLlm:
    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _call[T: BaseModel](
        self,
        purpose: Purpose,
        output: type[T],
        content: str | list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResult[T]:
        model = model_for(self._settings, purpose)
        usage = Usage(model, purpose)
        messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": _MAX_TOKENS[purpose],
            "system": _system(purpose, output),
        }
        if tools:
            request["tools"] = tools
        for attempt in range(2):
            try:
                response = self._client.messages.create(**request, messages=messages)
            except (
                Exception
            ) as exc:  # the SDK is not imported here; any failure means unavailable
                raise LlmUnavailableError(
                    f"{purpose} call failed: {exc}", usage
                ) from exc
            usage = usage + _usage(model, purpose, response)
            raw = "".join(b.text for b in response.content if b.type == "text")
            try:
                return LlmResult(output.model_validate_json(_extract_json(raw)), usage)
            except ValidationError as exc:
                error = exc
            if attempt == 0:
                messages.append({"role": "assistant", "content": raw or "(no text)"})
                messages.append(
                    {
                        "role": "user",
                        "content": f"That reply was not valid:\n{error}\n"
                        "Reply again with only the corrected JSON object.",
                    }
                )
        raise LlmOutputError(f"{purpose} output invalid after retry: {error}", usage)

    def read_page(self, image: bytes, media_type: str) -> LlmResult[PageText]:
        return self._call(
            "read_page",
            PageText,
            [
                _image(image, media_type),
                {"type": "text", "text": "Transcribe this page."},
            ],
        )

    def find_figures(self, image: bytes, media_type: str) -> LlmResult[FigureList]:
        return self._call(
            "figures",
            FigureList,
            [
                _image(image, media_type),
                {"type": "text", "text": "Find the figures on this page."},
            ],
        )

    def detect_chapters(
        self, pages: list[str], *, hint: str | None = None
    ) -> LlmResult[ChapterList]:
        text = "\n\n".join(f"--- page {i} ---\n{t}" for i, t in enumerate(pages, 1))
        if hint:
            text = f"Hint: {hint}\n\n{text}"
        return self._call("chapters", ChapterList, text)

    def rewrite_query(
        self, question: str, *, history: list[Turn]
    ) -> LlmResult[SearchQuery]:
        text = f"{_history(history)}\n\nLatest question: {question}"
        return self._call("rewrite", SearchQuery, text)

    def build_lesson(
        self, topic: str, *, passages: list[Passage], grade: int
    ) -> LlmResult[Lesson]:
        text = f"Grade: {grade}\nTopic: {topic}\n\nPassages:\n{_passages(passages)}"
        return self._call("lesson", Lesson, text)

    def answer_from_passages(
        self,
        question: str,
        *,
        history: list[Turn],
        passages: list[Passage],
        grade: int,
    ) -> LlmResult[BooksAnswer]:
        text = (
            f"Grade: {grade}\n\nPassages:\n{_passages(passages)}\n\n"
            f"{_history(history)}\n\nQuestion: {question}"
        )
        return self._call("answer", BooksAnswer, text)

    def answer_outside(
        self, question: str, *, history: list[Turn], grade: int
    ) -> LlmResult[OutsideAnswer]:
        text = f"Grade: {grade}\n\n{_history(history)}\n\nQuestion: {question}"
        return self._call("outside", OutsideAnswer, text, tools=[_WEB_SEARCH])

    def generate_questions(
        self, *, passages: list[Passage], count: int, grade: int
    ) -> LlmResult[QuestionSet]:
        if not passages:
            raise ValueError("no passages")
        text = (
            f"Grade: {grade}\nNumber of questions: {count}\n\n"
            f"Passages:\n{_passages(passages)}"
        )
        return self._call("questions", QuestionSet, text)
