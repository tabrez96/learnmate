import itertools
import re

from learnmate.rag.chunk import PageInput, chunk_pages


def prose(n: int, word: str = "rivers") -> str:
    return " ".join(f"Sentence {i} about {word} and rain." for i in range(n))


def one(text: str, chapter: int = 0, page: int = 1) -> list[PageInput]:
    return [PageInput(page=page, chapter=chapter, text=text)]


def test_short_chapter_is_one_chunk():
    text = "A short note about rivers.\nIt has two lines. " + "x" * 250
    chunks = chunk_pages(one(text))
    assert len(chunks) == 1
    assert (chunks[0].position, chunks[0].page) == (1, 1)
    assert chunks[0].text == " ".join(text.split())


def test_chunks_are_at_most_900_chars():
    pages = [PageInput(page=i + 1, chapter=0, text=prose(75)) for i in range(4)]
    chunks = chunk_pages(pages)
    assert len(chunks) > 3
    assert all(len(c.text) <= 900 for c in chunks)
    assert all(len(c.text) >= 600 for c in chunks[:-1])


def test_consecutive_chunks_overlap_by_about_120():
    chunks = chunk_pages(one(prose(200)))
    assert len(chunks) > 2
    for a, b in itertools.pairwise(chunks):
        shared = [n for n in range(1, 121) if a.text.endswith(b.text[:n]) and n >= 100]
        assert shared, (a.text[-130:], b.text[:130])


def test_no_chunk_spans_two_chapters():
    pages = [
        PageInput(page=1, chapter=0, text=prose(60, "alpha")),
        PageInput(page=2, chapter=1, text=prose(60, "beta")),
    ]
    chunks = chunk_pages(pages)
    assert not any("alpha" in c.text and "beta" in c.text for c in chunks)
    assert all(c.chapter == 0 for c in chunks if "alpha" in c.text)
    assert all(c.chapter == 1 for c in chunks if "beta" in c.text)
    first = next(c for c in chunks if c.chapter == 1)
    assert first.text.startswith("Sentence 0 about beta")


def test_heading_starts_new_chunk():
    body = "Water moves around. " * 20
    text = f"{body}\nRocks and Soil\n{'Soil is a mix. ' * 20}"
    chunks = chunk_pages(one(text))
    assert len(chunks) == 2
    assert chunks[1].text.startswith("Rocks and Soil")
    assert "Water" not in chunks[1].text


def test_heading_does_not_split_small_chunk():
    text = "Water moves around the world.\nRocks and Soil\n" + "Soil is a mix. " * 20
    chunks = chunk_pages(one(text))
    assert len(chunks) == 1
    assert "Rocks and Soil" in chunks[0].text


def test_wrapped_lines_are_not_headings():
    lines = [
        "The river carries water across the valley and through",
        "Cities that depend on it for drinking and for farming",
        "Every year the flood brings fresh soil to the fields and",
        "Farmers plant early so the crops are ready before the dry",
        "Season arrives and the water level falls again.",
    ]
    text = "\n".join(lines) * 1
    chunks = chunk_pages(one(text + "\n" + "More text follows here. " * 8))
    assert len(chunks) == 1


def test_page_is_where_chunk_text_starts():
    pages = [
        PageInput(page=1, chapter=0, text=prose(20, "alpha")[:700]),
        PageInput(page=2, chapter=0, text=prose(20, "beta")[:700]),
    ]
    chunks = chunk_pages(pages)
    assert chunks[0].page == 1
    assert chunks[1].page == 2


def test_positions_increase_across_chapters():
    pages = [
        PageInput(page=1, chapter=0, text=prose(60)),
        PageInput(page=2, chapter=1, text=prose(60)),
    ]
    chunks = chunk_pages(pages)
    assert [c.position for c in chunks] == list(range(1, len(chunks) + 1))
    assert {c.chapter for c in chunks} == {0, 1}


def test_long_sentence_and_long_word_are_cut():
    sentence = " ".join(f"word{i}" for i in range(300))
    token = "u" * 1500
    chunks = chunk_pages(one(f"{sentence}\n\n{token}"))
    assert all(len(c.text) <= 900 for c in chunks)
    joined = " ".join(c.text for c in chunks)
    assert all(f"word{i}" in joined for i in range(300))
    assert max(len(m) for m in re.findall(r"u+", joined)) >= 600


def test_empty_pages_make_no_chunks():
    pages = [
        PageInput(page=1, chapter=0, text=""),
        PageInput(page=2, chapter=0, text="   \n\n "),
    ]
    assert chunk_pages(pages) == []
