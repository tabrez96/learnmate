import pytest

from learnmate.models import Chapter, Chunk, Material, Subject
from learnmate.rag.keyword import fts_query, keyword_search


@pytest.fixture
def chapters(db):
    subject = Subject(name="Science", icon="flask")
    db.add(subject)
    db.flush()
    material = Material(subject_id=subject.id, title="Unit", kind="upload")
    db.add(material)
    db.flush()
    rows = [
        Chapter(material_id=material.id, name=f"Chapter {n}", position=n)
        for n in (1, 2)
    ]
    db.add_all(rows)
    db.flush()
    return material.id, rows


def add(db, material_id, chapter, position, text):
    row = Chunk(
        material_id=material_id,
        chapter_id=chapter.id,
        page=1,
        position=position,
        text=text,
    )
    db.add(row)
    db.flush()
    return row.id


def test_fts_query_splits_on_underscores():
    assert fts_query("water_cycle") == '"water" OR "cycle"'


def test_fts_query_quotes_words():
    assert fts_query('photo-synthesis "AND" *') == '"photo" OR "synthesis" OR "and"'
    assert fts_query("!!") is None


def test_keyword_search_ranks_matching_chunk_first(db, chapters):
    material_id, (one, _) = chapters
    twice = add(db, material_id, one, 1, "Photosynthesis needs light. Photosynthesis.")
    once = add(db, material_id, one, 2, "Photosynthesis happens in leaves of plants.")
    add(db, material_id, one, 3, "Rivers carry water to the sea.")
    hits = keyword_search(db, "photosynthesis", chapter_ids=[one.id])
    assert [h[0] for h in hits] == [twice, once]
    scores = [h[1] for h in hits]
    assert all(s > 0 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_keyword_search_is_limited_to_chapters(db, chapters):
    material_id, (one, two) = chapters
    add(db, material_id, two, 1, "Photosynthesis in the second chapter.")
    assert keyword_search(db, "photosynthesis", chapter_ids=[one.id]) == []
    assert keyword_search(db, "photosynthesis", chapter_ids=[]) == []
    assert len(keyword_search(db, "photosynthesis", chapter_ids=[two.id])) == 1


def test_keyword_search_matches_stemmed_word(db, chapters):
    material_id, (one, _) = chapters
    found = add(db, material_id, one, 1, "A river runs to the sea.")
    assert keyword_search(db, "rivers", chapter_ids=[one.id])[0][0] == found


def test_keyword_search_by_material(db, chapters):
    material_id, (one, _) = chapters
    other = Material(subject_id=1, title="Other", kind="upload")
    db.add(other)
    db.flush()
    mine = add(db, material_id, one, 1, "Photosynthesis in leaves.")
    db.add(Chunk(material_id=other.id, page=1, position=1, text="Photosynthesis too."))
    db.flush()
    assert [
        h[0] for h in keyword_search(db, "photosynthesis", material_ids=[material_id])
    ] == [mine]
    assert keyword_search(db, "photosynthesis", material_ids=[]) == []


def test_keyword_search_needs_one_scope(db, chapters):
    with pytest.raises(ValueError):
        keyword_search(db, "photosynthesis")
    with pytest.raises(ValueError):
        keyword_search(db, "photosynthesis", chapter_ids=[1], material_ids=[1])
