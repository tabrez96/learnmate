"""Types for the one interface every AI call goes through."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from learnmate.config import Settings

type Purpose = Literal[
    "read_page",
    "chapters",
    "rewrite",
    "lesson",
    "answer",
    "outside",
    "questions",
    "figures",
]
FAST_PURPOSES = frozenset({"read_page", "chapters", "rewrite", "figures"})


def model_for(settings: Settings, purpose: Purpose) -> str:
    return settings.model_fast if purpose in FAST_PURPOSES else settings.model_main


@dataclass(frozen=True)
class Usage:
    """Tokens and web searches of one call, retries included."""

    model: str
    purpose: Purpose
    input_tokens: int = 0
    output_tokens: int = 0
    web_searches: int = 0

    def __add__(self, other: Usage) -> Usage:
        if (self.model, self.purpose) != (other.model, other.purpose):
            raise ValueError("cannot add usage of different models or purposes")
        return Usage(
            self.model,
            self.purpose,
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.web_searches + other.web_searches,
        )


@dataclass(frozen=True)
class LlmResult[T: BaseModel]:
    value: T
    usage: Usage


class LlmError(Exception):
    """Every error carries the usage so the spend is still recorded."""

    def __init__(self, message: str, usage: Usage) -> None:
        super().__init__(message)
        self.usage = usage


class LlmOutputError(LlmError): ...  # output still invalid after the one retry


class LlmUnavailableError(LlmError): ...  # the provider call itself failed


class Passage(BaseModel):
    id: int
    text: str
    material: str
    chapter: str
    page: int | None = None
    figure_id: int | None = None


class Turn(BaseModel):
    role: Literal["mentor", "student"]
    text: str


class PageText(BaseModel):
    text: str


class ChapterGuess(BaseModel):
    name: str
    start_page: int = Field(ge=1)


class ChapterList(BaseModel):
    chapters: list[ChapterGuess]


class SearchQuery(BaseModel):
    query: str = Field(min_length=1)


class QuickCheck(BaseModel):
    prompt: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str


class LessonStep(BaseModel):
    title: str
    body: str
    check: QuickCheck
    passage_ids: list[int]


class Lesson(BaseModel):
    steps: list[LessonStep] = Field(min_length=1)


class BooksAnswer(BaseModel):
    covered: bool
    text: str
    passage_ids: list[int]
    visual: dict[str, Any] | None = None


class OutsideAnswer(BaseModel):
    text: str
    source_url: str
    visual: dict[str, Any] | None = None


class Question(BaseModel):
    prompt: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str
    passage_id: int


class QuestionSet(BaseModel):
    questions: list[Question] = Field(min_length=1)


class FigureBox(BaseModel):
    description: str
    box: list[float] = Field(min_length=4, max_length=4)  # x0, y0, x1, y1 as 0..1


class FigureList(BaseModel):
    figures: list[FigureBox]


class Llm(Protocol):
    def read_page(self, image: bytes, media_type: str) -> LlmResult[PageText]: ...

    def detect_chapters(
        self, pages: list[str], *, hint: str | None = None
    ) -> LlmResult[ChapterList]: ...

    def rewrite_query(
        self, question: str, *, history: list[Turn]
    ) -> LlmResult[SearchQuery]: ...

    def build_lesson(
        self, topic: str, *, passages: list[Passage], grade: int
    ) -> LlmResult[Lesson]: ...

    def answer_from_passages(
        self,
        question: str,
        *,
        history: list[Turn],
        passages: list[Passage],
        grade: int,
    ) -> LlmResult[BooksAnswer]: ...

    def answer_outside(
        self, question: str, *, history: list[Turn], grade: int
    ) -> LlmResult[OutsideAnswer]: ...

    def generate_questions(
        self, *, passages: list[Passage], count: int, grade: int
    ) -> LlmResult[QuestionSet]: ...

    def find_figures(self, image: bytes, media_type: str) -> LlmResult[FigureList]: ...
