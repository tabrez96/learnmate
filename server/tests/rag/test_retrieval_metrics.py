"""Harness checks that need no embedding model: metrics, matchers, corpus shape."""

from dataclasses import replace

from learnmate.models import Chunk, Subject
from learnmate.rag.embed import FakeEmbedder
from learnmate.rag.keyword import keyword_search
from learnmate.rag.search import Scope, SearchHit
from tests.rag.retrieval_eval import (
    EVAL,
    Outcome,
    add_material,
    build_corpus,
    floor_dependent,
    load_corpus,
    mean_seconds,
    mrr,
    normalise,
    page_matcher,
    recall_at_k,
    report,
    run_question,
    snippet_matcher,
)
from tests.rag.test_search import WordEmbedder


def outcome(rank, kind="exact", passages=1):
    return Outcome("q", kind, "question?", rank, passages, 0.5, 0, 0.0)


def hit(text="text", chunk_ids=(1,)):
    return SearchHit(chunk_ids[0], list(chunk_ids), 1, 1, 1, text, 0.1)


def test_set_composition():
    corpus = load_corpus()
    questions = corpus["questions"]
    kinds = [q["kind"] for q in questions]
    assert len({q["id"] for q in questions}) == len(questions)
    assert sum(k != "off_topic" for k in kinds) == 30
    assert kinds.count("paraphrase") >= 10
    assert kinds.count("exact") >= 8
    assert kinds.count("handwritten") >= 6
    assert kinds.count("off_topic") >= 5
    assert all(q["expected"] == [] for q in questions if q["kind"] == "off_topic")
    free = [q for q in questions if q.get("keyword_free")]
    assert len(free) >= 4
    assert all(q["kind"] == "paraphrase" for q in free)
    for subject in {q["subject"] for q in questions}:
        assert sum(q["subject"] == subject for q in free) >= 2
    for subject in {q["subject"] for q in questions}:
        mine = [q for q in questions if q["subject"] == subject]
        assert sum(q["kind"] != "off_topic" for q in mine) >= 12

    typed, vision = [], []
    for spec in corpus["subjects"]:
        for material in spec["materials"]:
            for chapter in material["chapters"]:
                for page in chapter["pages"]:
                    if "photo" in page:
                        assert (EVAL / "photos" / page["photo"]).is_file()
                        vision.append(normalise(page["vision_text"]))
                    else:
                        typed.append(normalise(page["text"]))
    for q in questions:
        for snippet in q["expected"]:
            s = normalise(snippet)
            assert len(s) < 80, q["id"]
            in_typed = any(s in t for t in typed)
            if q["kind"] == "handwritten":
                assert any(s in v for v in vision) and not in_typed, q["id"]
            else:
                assert in_typed, q["id"]


def test_keyword_free_questions_have_no_keyword_hits(db, settings):
    corpus = load_corpus()
    chapter_ids = build_corpus(db, settings, FakeEmbedder("fake"), corpus)
    flagged = [q for q in corpus["questions"] if q.get("keyword_free")]
    hits = {
        q["id"]: keyword_search(
            db, q["question"], chapter_ids=chapter_ids[q["subject"]]
        )
        for q in flagged
    }
    assert not {k: v for k, v in hits.items() if v}, (
        f"keyword-free questions with keyword hits: {hits}"
    )


def test_recall_and_mrr_maths():
    rows = [outcome(1), outcome(2), outcome(None), outcome(None, "off_topic", 0)]
    assert recall_at_k(rows) == 2 / 3
    assert mrr(rows) == (1 + 0.5) / 3


def test_metrics_empty():
    rows = [outcome(None, "off_topic", 0)]
    assert recall_at_k(rows) == 0.0
    assert mrr(rows) == 0.0
    assert recall_at_k([]) == mrr([]) == 0.0


def test_snippet_matcher_normalises():
    match = snippet_matcher(["Light  Travels"])
    assert match(hit("the LIGHT\ntravels fast"))
    assert not match(hit("sound moves slowly"))


def add_plants(db):
    subject = Subject(name="Science", icon="flask")
    db.add(subject)
    db.flush()
    chapter_ids = add_material(
        db,
        WordEmbedder(),
        subject=subject,
        title="Book",
        chapter_names=["One", "Two"],
        starts=[1, 2],
        texts=["A plant makes food.", "A river runs to the sea."],
    )
    return chapter_ids


def test_page_matcher(db):
    add_plants(db)
    on_page_1, on_page_2 = db.query(Chunk).order_by(Chunk.page).all()
    assert page_matcher(db, {("Book", 1)})(hit(chunk_ids=(on_page_1.id,)))
    assert not page_matcher(db, {("Book", 1)})(hit(chunk_ids=(on_page_2.id,)))
    assert page_matcher(db, {("Book", 2)})(hit(chunk_ids=(on_page_1.id, on_page_2.id)))


def test_add_material_with_fake_embedder(db):
    subject = Subject(name="Science", icon="flask")
    db.add(subject)
    db.flush()
    ids = add_material(
        db,
        FakeEmbedder("fake"),
        subject=subject,
        title="Book",
        chapter_names=["One", "Two"],
        starts=[1, 2],
        texts=["First page.", "Second page."],
    )
    assert len(ids) == 2
    chunks = db.query(Chunk).order_by(Chunk.page).all()
    assert [c.chapter_id for c in chunks] == ids
    assert all(c.embedding and c.embed_model == "fake" for c in chunks)


def test_run_question_off_topic_rejected_with_fake_floor(db):
    scope = Scope.chapters(add_plants(db))
    off = run_question(
        db,
        WordEmbedder(),
        scope,
        id="o1",
        kind="off_topic",
        question="football scores",
        relevant=snippet_matcher([]),
        floor=0.35,
    )
    assert off.passages == 0
    assert off.rank is None
    on = run_question(
        db,
        WordEmbedder(),
        scope,
        id="q1",
        kind="exact",
        question="plant",
        relevant=snippet_matcher(["makes food"]),
        floor=0.35,
    )
    assert on.rank == 1
    assert on.keyword_hits == 1


def test_floor_dependent():
    with_hits = Outcome("a", "exact", "q?", 1, 1, 0.5, 2, 0.0)
    without = Outcome("b", "paraphrase", "q?", 1, 1, 0.5, 0, 0.0)
    off = Outcome("c", "off_topic", "q?", None, 0, 0.3, 0, 0.0)
    assert floor_dependent([with_hits, without, off]) == [without]


def test_report_lines():
    rows = [
        outcome(1),
        outcome(None),
        outcome(None, "off_topic", 0),
        outcome(None, "off_topic", 2),
    ]
    text = report("demo", rows, 0.4)
    assert "HIT@1" in text
    assert "MISS" in text
    assert "REJECTED" in text
    assert "ANSWERED" in text
    assert "recall@6=0.500" in text
    assert "floor=0.40" in text
    assert "min floor-dependent cos=0.500" in text
    assert "s/question=0.000" in text


def test_mean_seconds():
    rows = [replace(outcome(1), seconds=1.0), replace(outcome(None), seconds=2.0)]
    assert mean_seconds(rows) == 1.5
    assert mean_seconds([]) == 0.0


def test_expected_pages_parse_file_and_page():
    from tests.rag.test_retrieval_real import expected_pages

    assert expected_pages(["civics-ch3.pdf:2", "a.b.pdf:10"]) == {
        ("civics-ch3.pdf", 2),
        ("a.b.pdf", 10),
    }
