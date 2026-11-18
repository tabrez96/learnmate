"""Splits a material's page texts into overlapping chunks, one chapter at a time. Pure."""

import re
from dataclasses import dataclass
from itertools import groupby

CHUNK_SIZE = 800  # target length; a chunk grows until the next piece would pass this
OVERLAP = 120  # tail of the previous chunk repeated at the start of the next
PIECE_MAX = CHUNK_SIZE - OVERLAP  # longest piece, so overlap + piece stays under 900
HEADING_MAX = 80  # a heading is one short line
MIN_BEFORE_HEADING = (
    200  # a heading only starts a new chunk once the current one has this much text
)


@dataclass(frozen=True)
class PageInput:
    page: int  # 1-based page number in the material
    chapter: int  # 0-based index of the chapter the page belongs to
    text: str


@dataclass(frozen=True)
class ChunkDraft:
    chapter: int  # 0-based chapter index (same as PageInput.chapter)
    page: int  # page where the chunk's own (non-overlap) text starts
    position: int  # 1-based, increasing across the whole material
    text: str


@dataclass(frozen=True)
class _Piece:
    text: str
    page: int
    heading: bool


def chunk_pages(pages: list[PageInput]) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for chapter, group in groupby(pages, key=lambda p: p.chapter):
        pieces = [piece for p in group for piece in _pieces(p.text, p.page)]
        _pack(chapter, pieces, drafts)
    return drafts


def _pack(chapter: int, pieces: list[_Piece], drafts: list[ChunkDraft]) -> None:
    current = ""
    start_page = 0
    has_own = False

    def emit() -> None:
        drafts.append(
            ChunkDraft(
                chapter=chapter,
                page=start_page,
                position=len(drafts) + 1,
                text=current,
            )
        )

    for piece in pieces:
        if piece.heading and has_own and len(current) >= MIN_BEFORE_HEADING:
            emit()
            current, has_own = "", False
        elif has_own and len(current) + 1 + len(piece.text) > CHUNK_SIZE:
            emit()
            current, has_own = _tail(current), False
        current = piece.text if not current else current + "\n" + piece.text
        if not has_own:
            start_page = piece.page
            has_own = True
    if has_own:
        emit()


def _pieces(text: str, page: int) -> list[_Piece]:
    paragraphs = [
        [" ".join(line.split()) for line in para.splitlines() if line.strip()]
        for para in re.split(r"\n\s*\n", text)
    ]
    paragraphs = [lines for lines in paragraphs if lines]
    flat = [line for lines in paragraphs for line in lines]
    pieces: list[_Piece] = []
    seen = 0
    for lines in paragraphs:
        words: list[str] = []
        for line in lines:
            before = flat[seen - 1] if seen else None
            after = flat[seen + 1] if seen + 1 < len(flat) else None
            seen += 1
            if _is_heading(line, before, after):
                pieces.extend(_paragraph_pieces(words, page))
                words = []
                pieces.append(_Piece(line, page, True))
            else:
                words.append(line)
        pieces.extend(_paragraph_pieces(words, page))
    return pieces


def _paragraph_pieces(lines: list[str], page: int) -> list[_Piece]:
    if not lines:
        return []
    return [_Piece(part, page, False) for part in _split_long(" ".join(lines))]


def _is_heading(line: str, before: str | None, after: str | None) -> bool:
    """A short title-like line between finished text and the start of a new sentence."""
    return (
        len(line) <= HEADING_MAX
        and line[-1] not in ".!?,;:"
        and (line[0].isupper() or line[0].isdigit())
        and (before is None or before[-1] in ".!?:")
        and after is not None
        and (after[0].isupper() or after[0].isdigit())
    )


def _split_long(text: str) -> list[str]:
    if len(text) <= PIECE_MAX:
        return [text]
    parts: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > PIECE_MAX:
            if current:
                parts.append(current)
                current = ""
            cut = sentence.rfind(" ", 0, PIECE_MAX)
            cut = cut if cut > 0 else PIECE_MAX
            parts.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > PIECE_MAX:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        parts.append(current)
    return parts


def _tail(text: str) -> str:
    tail = text[-OVERLAP:]
    if len(text) > OVERLAP and not text[-OVERLAP - 1].isspace():
        for i, ch in enumerate(tail):
            if ch.isspace():
                tail = tail[i + 1 :]
                break
    return tail.strip()
