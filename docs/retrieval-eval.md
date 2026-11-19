# Retrieval evaluation

## What it measures

Every question is searched with the same code the mentor uses (`learnmate.rag.search.search`), inside the chapters of its subject.

- **recall@6**: the share of answerable questions where one of the six returned passages contains the answer.
- **MRR**: the mean of 1 / rank of the first passage with the answer (0 when missed).
- **The gate**: `tests/rag/test_retrieval_eval.py` fails when recall@6 is below 0.85.
- **Off-topic questions** must return no passages. The highest cosine of any off-topic question must be below the relevance floor, and the floor must not exceed the lowest cosine of any answerable question with no keyword hit (a question with a keyword hit skips the floor).

The committed set is `server/tests/rag/eval/corpus.yaml`: two invented subjects (Science, Civics), typed textbook pages, three invented notebook pages photographed with a phone, 30 answerable questions (paraphrased, exact-term and notebook-only) and 6 off-topic ones. The notebook photos are read through `iter_pages` and `page_text` with recorded vision output (`vision_text`), so no AI call is made. The real embedding model runs.

## Running

```sh
cd server
EMBED_CACHE_DIR=~/.cache/fastembed pytest tests/rag          # committed set; downloads the model once (about 70 MB)
EMBED_CACHE_DIR=~/.cache/fastembed pytest tests/rag --real   # also the real set below (needs ANTHROPIC_API_KEY)
```

Without `EMBED_CACHE_DIR` the committed eval is skipped; the metric and corpus-shape tests always run. Without `--real` the real set is skipped and never calls the AI API.

## Adding real pages

Put school book pages (PDF, Word, photos) in `server/data/eval/real/`; git ignores it. One file is one material, titled with its file name. Don't use colons in file names. The run reads them with the real vision model and detects chapters, like an upload.

## Writing questions

Add `server/data/eval/real/questions.yaml`, about 20 questions:

```yaml
- id: r01
  question: What does Article 21 protect?
  expected: ["civics-ch3.pdf:2"] # file name : page number (1-based within that file)
- id: r20
  question: Who won the football world cup in 2018?
  off_topic: true
```

Mix paraphrased questions, exact-term questions and notebook-only questions, plus a few off-topic ones. A page counts as found when a returned passage includes a chunk that starts on that page, so a chunk that starts at the bottom of page 2 and runs into page 3 counts as page 2. The run prints one line per question (`HIT@n`, `MISS`, `REJECTED`, `ANSWERED`) and a summary line.

## Changing the committed set

Edit `corpus.yaml`. After changing a notebook page's `vision_text`, run `python tests/rag/eval/make_photos.py` to redraw the photos. Keep `test_set_composition` green: 30 answerable questions, and notebook-only answers present only in `vision_text`.

Questions marked `keyword_free: true` must share no word (after stemming) with their subject's material, so the test can check them without the model (`test_keyword_free_questions_have_no_keyword_hits`). The flag only selects questions for that test. The relevance floor applies to every answerable question with no keyword match, marked or not, so include all of them when tuning the floor.

## The relevance floor

`RAG_MIN_SIMILARITY` is the cosine below which a search returns nothing when keyword search found nothing. The floor only applies to questions with no keyword match, so it is set to the midpoint between the highest off-topic cosine (O) and the lowest cosine of an answerable question with no keyword match (A), rounded to two decimals. The test also checks that every answerable question still gets passages.

Current value: 0.53, tuned on the retrieval eval for bge-small-en-v1.5 (off-topic max 0.499 on o02, floor-dependent min 0.555 on q09). When the floor needs re-tuning, the failure message of `test_off_topic_questions_get_no_passages` prints O, A (`floor-dependent min cos`), `suggested` and the ids at the edges.

Before changing the floor, run both sets: the real run's summary line must also show O below the floor and the floor at most A.
