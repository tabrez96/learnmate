"""Wraps any provider so every call's usage is priced and recorded."""

from collections.abc import Callable

from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from learnmate.clock import Clock
from learnmate.config import Settings
from learnmate.llm.budget import record_usage
from learnmate.llm.types import (
    BooksAnswer,
    ChapterList,
    FigureList,
    Lesson,
    Llm,
    LlmError,
    LlmResult,
    OutsideAnswer,
    PageText,
    Passage,
    QuestionSet,
    SearchQuery,
    Turn,
    Usage,
)


class MeteredLlm:
    def __init__(
        self,
        inner: Llm,
        session_factory: sessionmaker[Session],
        settings: Settings,
        clock: Clock,
    ) -> None:
        self.inner = inner
        self._session_factory = session_factory
        self._settings = settings
        self._clock = clock

    def _run[T: BaseModel](self, call: Callable[[], LlmResult[T]]) -> LlmResult[T]:
        try:
            result = call()
        except LlmError as exc:
            self._record(exc.usage)
            raise
        self._record(result.usage)
        return result

    def _record(self, usage: Usage) -> None:
        # Its own short session: the row is committed whatever the caller's transaction does.
        with self._session_factory() as db:
            record_usage(db, self._settings, self._clock, usage)

    def read_page(self, image: bytes, media_type: str) -> LlmResult[PageText]:
        return self._run(lambda: self.inner.read_page(image, media_type))

    def detect_chapters(
        self, pages: list[str], *, hint: str | None = None
    ) -> LlmResult[ChapterList]:
        return self._run(lambda: self.inner.detect_chapters(pages, hint=hint))

    def rewrite_query(
        self, question: str, *, history: list[Turn]
    ) -> LlmResult[SearchQuery]:
        return self._run(lambda: self.inner.rewrite_query(question, history=history))

    def build_lesson(
        self, topic: str, *, passages: list[Passage], grade: int
    ) -> LlmResult[Lesson]:
        return self._run(
            lambda: self.inner.build_lesson(topic, passages=passages, grade=grade)
        )

    def answer_from_passages(
        self,
        question: str,
        *,
        history: list[Turn],
        passages: list[Passage],
        grade: int,
    ) -> LlmResult[BooksAnswer]:
        return self._run(
            lambda: self.inner.answer_from_passages(
                question, history=history, passages=passages, grade=grade
            )
        )

    def answer_outside(
        self, question: str, *, history: list[Turn], grade: int
    ) -> LlmResult[OutsideAnswer]:
        return self._run(
            lambda: self.inner.answer_outside(question, history=history, grade=grade)
        )

    def generate_questions(
        self, *, passages: list[Passage], count: int, grade: int
    ) -> LlmResult[QuestionSet]:
        return self._run(
            lambda: self.inner.generate_questions(
                passages=passages, count=count, grade=grade
            )
        )

    def find_figures(self, image: bytes, media_type: str) -> LlmResult[FigureList]:
        return self._run(lambda: self.inner.find_figures(image, media_type))
