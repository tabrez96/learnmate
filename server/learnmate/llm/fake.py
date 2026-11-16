"""A provider with fixed outputs and fixed usage, for tests and offline runs."""

from learnmate.config import Settings
from learnmate.llm.types import (
    BooksAnswer,
    ChapterGuess,
    ChapterList,
    FigureList,
    Lesson,
    LessonStep,
    LlmResult,
    OutsideAnswer,
    PageText,
    Passage,
    Purpose,
    Question,
    QuestionSet,
    QuickCheck,
    SearchQuery,
    Turn,
    Usage,
    model_for,
)

_OPTIONS = ["A", "B", "C", "D"]


class FakeLlm:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.calls: list[Purpose] = []

    def _result[T](self, purpose: Purpose, value: T) -> LlmResult[T]:
        self.calls.append(purpose)
        searches = 1 if purpose == "outside" else 0
        usage = Usage(model_for(self._settings, purpose), purpose, 100, 50, searches)
        return LlmResult(value, usage)

    def read_page(self, image: bytes, media_type: str) -> LlmResult[PageText]:
        page = PageText(text="Plants make food from sunlight.")
        return self._result("read_page", page)

    def detect_chapters(
        self, pages: list[str], *, hint: str | None = None
    ) -> LlmResult[ChapterList]:
        guess = ChapterGuess(name=hint or "Chapter 1", start_page=1)
        return self._result("chapters", ChapterList(chapters=[guess]))

    def rewrite_query(
        self, question: str, *, history: list[Turn]
    ) -> LlmResult[SearchQuery]:
        return self._result("rewrite", SearchQuery(query=question))

    def build_lesson(
        self, topic: str, *, passages: list[Passage], grade: int
    ) -> LlmResult[Lesson]:
        check = QuickCheck(
            prompt="Which one?", options=_OPTIONS, correct_index=0, explanation="A."
        )
        step = LessonStep(
            title=topic,
            body="Step one.",
            check=check,
            passage_ids=[p.id for p in passages[:1]],
        )
        return self._result("lesson", Lesson(steps=[step]))

    def answer_from_passages(
        self,
        question: str,
        *,
        history: list[Turn],
        passages: list[Passage],
        grade: int,
    ) -> LlmResult[BooksAnswer]:
        ids = [p.id for p in passages[:1]]
        text = "From your notes." if passages else ""
        answer = BooksAnswer(covered=bool(passages), text=text, passage_ids=ids)
        return self._result("answer", answer)

    def answer_outside(
        self, question: str, *, history: list[Turn], grade: int
    ) -> LlmResult[OutsideAnswer]:
        answer = OutsideAnswer(
            text="From the web.", source_url="https://example.org/source"
        )
        return self._result("outside", answer)

    def generate_questions(
        self, *, passages: list[Passage], count: int, grade: int
    ) -> LlmResult[QuestionSet]:
        if not passages:
            raise ValueError("no passages")
        questions = [
            Question(
                prompt=f"Question {i + 1}?",
                options=_OPTIONS,
                correct_index=0,
                explanation="A.",
                passage_id=passages[i % len(passages)].id,
            )
            for i in range(count)
        ]
        return self._result("questions", QuestionSet(questions=questions))

    def find_figures(self, image: bytes, media_type: str) -> LlmResult[FigureList]:
        return self._result("figures", FigureList(figures=[]))
