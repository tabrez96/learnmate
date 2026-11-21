"""The lesson: which passages to send, checking citations, and the lesson inside the plan. Pure."""

import copy
from collections.abc import Callable
from dataclasses import dataclass

from learnmate.llm.types import Lesson, Passage
from learnmate.rag.chunk import HEADING_MAX

LESSON_MAX_CHARS = 24_000  # total passage text sent for one lesson


class MentorError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


type ChapterKey = tuple[int, int | None]  # (material_id, chapter_id)


@dataclass(frozen=True)
class ScopeChunk:
    id: int
    material_id: int
    chapter_id: int | None
    material: str  # material title
    chapter: str  # chapter name, "" when none
    page: int | None
    position: int
    text: str

    @property
    def key(self) -> ChapterKey:
        return (self.material_id, self.chapter_id)


# Chunk ids of the best passage for a query in a chapter, best first.
type Retrieve = Callable[[ChapterKey, str], list[int]]


def heading_of(text: str) -> str | None:
    """The chunker starts a new chunk at a heading, so a heading is the first line."""
    first, _, rest = text.partition("\n")
    heading = first.strip()
    if (
        heading
        and rest.strip()
        and len(first) <= HEADING_MAX
        and heading[-1] not in ".!?,;:"
    ):
        return heading
    return None


def group_by_chapter(chunks: list[ScopeChunk]) -> list[list[ScopeChunk]]:
    groups: list[list[ScopeChunk]] = []
    for chunk in chunks:
        if groups and groups[-1][0].key == chunk.key:
            groups[-1].append(chunk)
        else:
            groups.append([chunk])
    return groups


def _fit(chunks: list[ScopeChunk], limit: int) -> list[ScopeChunk]:
    kept: list[ScopeChunk] = []
    total = 0
    for chunk in chunks:
        if kept and total + len(chunk.text) > limit:
            continue
        kept.append(chunk)
        total += len(chunk.text)
    return kept


def select_for_chapter(
    chunks: list[ScopeChunk], retrieve: Retrieve, limit: int
) -> list[ScopeChunk]:
    if sum(len(c.text) for c in chunks) <= limit:
        return chunks
    candidates = [chunks[0].chapter, *(heading_of(c.text) for c in chunks)]
    queries = list(dict.fromkeys(q for q in candidates if q))
    by_id = {c.id: c for c in chunks}
    priority: list[ScopeChunk] = []
    seen: set[int] = set()
    for query in queries:
        for chunk_id in retrieve(chunks[0].key, query):
            if chunk_id in by_id and chunk_id not in seen:
                seen.add(chunk_id)
                priority.append(by_id[chunk_id])
    priority.extend(c for c in chunks if c.id not in seen)
    kept = _fit(priority, limit)
    return sorted(kept, key=lambda c: c.position)


def select_passages(
    chunks: list[ScopeChunk], retrieve: Retrieve, max_chars: int = LESSON_MAX_CHARS
) -> list[Passage]:
    groups = group_by_chapter(chunks)
    if not groups:
        return []
    share = max_chars // len(groups)
    kept: list[ScopeChunk] = []
    for group in groups:
        kept.extend(select_for_chapter(group, retrieve, share))
    return [
        Passage(
            id=c.id, text=c.text, material=c.material, chapter=c.chapter, page=c.page
        )
        for c in kept
    ]


def citations_valid(lesson: Lesson, sent_ids: set[int]) -> bool:
    return all(
        step.passage_ids and all(i in sent_ids for i in step.passage_ids)
        for step in lesson.steps
    )


def lesson_entry(lesson: Lesson, passages: list[Passage]) -> dict:
    by_id = {p.id: p for p in passages}
    return {
        "steps": [
            {
                "title": s.title,
                "body": s.body,
                "check": {
                    "prompt": s.check.prompt,
                    "options": s.check.options,
                    "correct_index": s.check.correct_index,
                    "explanation": s.check.explanation,
                },
                "passage_ids": s.passage_ids,
                "sources": [
                    {
                        "passage_id": i,
                        "material": by_id[i].material,
                        "chapter": by_id[i].chapter,
                        "page": by_id[i].page,
                    }
                    for i in s.passage_ids
                ],
                "answer_index": None,
            }
            for s in lesson.steps
        ]
    }


def lesson_step(plan: dict) -> dict:
    for step in plan["steps"]:
        if step["key"] == "lesson":
            return step
    raise MentorError(409, "This session has no lesson")


def with_lesson(plan: dict, entry: dict) -> dict:
    new = copy.deepcopy(plan)
    lesson_step(new)["lesson"] = entry
    return new


def answer_check(plan: dict, index: int, answer_index: int) -> tuple[dict, bool]:
    new = copy.deepcopy(plan)
    step = lesson_step(new)
    if "lesson" not in step:
        raise MentorError(409, "The lesson hasn't started")
    steps = step["lesson"]["steps"]
    if not 0 <= index < len(steps):
        raise MentorError(404, "Lesson step not found")
    target = steps[index]
    if target["answer_index"] is not None:
        raise MentorError(409, "Already answered")
    target["answer_index"] = answer_index
    return new, answer_index == target["check"]["correct_index"]
