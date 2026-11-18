from learnmate.ingest.chapters import clean, given_names, page_chapters
from learnmate.llm.types import ChapterGuess


def g(name, page):
    return ChapterGuess(name=name, start_page=page)


def pairs(chapters):
    return [(c.name, c.start_page) for c in chapters]


def test_given_names_split_and_dedupe():
    assert given_names("Light; sound\nLight, Magnets ") == ["Light", "sound", "Magnets"]
    assert given_names(None) == []
    assert given_names("  ") == []


def test_clean_sorts_and_drops_bad_guesses():
    guesses = [g("B", 4), g("Late", 99), g("A", 2), g("Dup", 4), g(" ", 3)]
    result = clean(guesses, 6, given=[], fallback="Title")
    assert pairs(result) == [("A", 1), ("B", 4)]


def test_clean_empty_falls_back():
    assert pairs(clean([], 3, given=[], fallback="Title")) == [("Title", 1)]
    assert pairs(clean([], 3, given=["Light"], fallback="Title")) == [("Light", 1)]
    assert pairs(clean([], 3, given=["A", "B"], fallback="Title")) == [("Title", 1)]


def test_clean_uses_given_names_when_counts_match():
    result = clean([g("x", 1), g("y", 3)], 5, given=["Water", "Rocks"], fallback="T")
    assert pairs(result) == [("Water", 1), ("Rocks", 3)]


def test_clean_keeps_given_spelling_on_match():
    guesses = [g("Chapter 3: Light", 1), g("Sound", 4), g("Magnets", 7)]
    result = clean(guesses, 9, given=["light"], fallback="T")
    assert [c.name for c in result] == ["light", "Sound", "Magnets"]


def test_clean_does_not_match_inside_words():
    guesses = [g("Flight", 1), g("Sound", 4)]
    result = clean(guesses, 9, given=["Light"], fallback="T")
    assert [c.name for c in result] == ["Flight", "Sound"]


def test_clean_cuts_long_names():
    assert len(clean([g("x" * 300, 1)], 2, given=[], fallback="T")[0].name) == 200


def test_page_chapters_maps_pages():
    assert page_chapters([1, 3], 4) == [0, 0, 1, 1]
