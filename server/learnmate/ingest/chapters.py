"""Chapter names given at upload and clean-up of the model's chapter guesses. Pure."""

import re

from learnmate.llm.types import ChapterGuess

NAME_MAX = 200  # the chapter.name column size


def given_names(hint: str | None) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[\n;,]", hint or ""):
        name = part.strip()[:NAME_MAX]
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            names.append(name)
    return names


def clean(
    guesses: list[ChapterGuess],
    page_count: int,
    *,
    given: list[str],
    fallback: str,
) -> list[ChapterGuess]:
    kept: list[ChapterGuess] = []
    for g in sorted(guesses, key=lambda g: g.start_page):
        if g.start_page > page_count or not g.name.strip():
            continue
        if kept and kept[-1].start_page == g.start_page:
            continue
        kept.append(g)
    if not kept:
        name = given[0] if len(given) == 1 else fallback
        kept = [ChapterGuess(name=name, start_page=1)]
    kept[0] = ChapterGuess(name=kept[0].name, start_page=1)

    if len(given) == len(kept):
        names = list(given)
    else:
        names = [_given_match(g.name, given) or g.name for g in kept]
    return [
        ChapterGuess(name=name[:NAME_MAX], start_page=g.start_page)
        for name, g in zip(names, kept, strict=True)
    ]


def _words(name: str) -> list[str]:
    return re.findall(r"\w+", name.casefold())


def _contains(words: list[str], part: list[str]) -> bool:
    n = len(part)
    return n > 0 and any(words[i : i + n] == part for i in range(len(words) - n + 1))


def _given_match(name: str, given: list[str]) -> str | None:
    """A given name that appears in `name` (or contains it) as whole words."""
    words = _words(name)
    for candidate in given:
        c = _words(candidate)
        if _contains(words, c) or _contains(c, words):
            return candidate
    return None


def page_chapters(starts: list[int], page_count: int) -> list[int]:
    """For pages 1..page_count, the 0-based index of the chapter each page is in."""
    return [
        max(i for i, start in enumerate(starts) if start <= page)
        for page in range(1, page_count + 1)
    ]
