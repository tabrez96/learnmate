# Retrieval evaluation

## What it measures

Every question is searched with the same code the mentor uses (`learnmate.rag.search.search`), inside the chapters of its subject.

- **recall@6**: the share of answerable questions where one of the six returned passages contains the answer.
- **MRR**: the mean of 1 / rank of the first passage with the answer (0 when missed).
- **s/question**: mean wall time of one search, reranker included, after the models are loaded.
- **The gate**: `tests/rag/test_retrieval_eval.py` fails when recall@6 is below 0.85.
- **Off-topic questions** must return no passages. The highest cosine of any off-topic question must be below the relevance floor, and the floor must not exceed the lowest cosine of any answerable question with no keyword hit (a question with a keyword hit skips the floor).

The committed set is `server/tests/rag/eval/corpus.yaml`: two invented subjects (Science, Civics), typed textbook pages, three invented notebook pages photographed with a phone, 30 answerable questions (paraphrased, exact-term and notebook-only) and 6 off-topic ones. The notebook photos are read through `iter_pages` and `page_text` with recorded vision output (`vision_text`), so no AI call is made. The real embedding model runs.

## Running

```sh
cd server
EMBED_CACHE_DIR=~/.cache/fastembed pytest tests/rag -s       # committed set; downloads the models once (about 70 MB, plus the reranker, about 1.1 GB)
EMBED_CACHE_DIR=~/.cache/fastembed pytest tests/rag --real   # also the real set below (needs ANTHROPIC_API_KEY)
```

The eval runs every question twice, with the reranker off and on, and prints both reports.

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

Current value: 0.53, tuned on the retrieval eval for bge-small-en-v1.5 (off-topic max 0.499 on o02, floor-dependent min 0.555 on q09). When the floor needs re-tuning, the failure message of `test_off_topic_questions_get_no_passages` prints O, A (`floor-dependent min cos`), `suggested` and the ids at the edges; copy the numbers here and into the comment in `server/learnmate/config.py`.

Before changing the floor, run both sets: the real run's summary line must also show O below the floor and the floor at most A.

## The reranker

When `RERANK_ENABLED` is on, `search` rescores the fused top 20 candidates with the cross-encoder `BAAI/bge-reranker-base` (`RERANK_MODEL`) before neighbouring chunks are merged. The relevance floor runs first, so the reranker never turns an empty result into an answer.

The rule: it is on by default only if committed-set recall@6 with it is strictly higher than without and it takes at most 1.5 s per question. `test_rerank_default_matches_eval` enforces this: it fails when the default configuration scores below the other, unless the reranker is off because it is too slow.

| Set       | Rerank | recall@6 | MRR     | s/question |
| --------- | ------ | -------- | ------- | ---------- |
| committed | off    | 1.000    | 0.950   | 0.007      |
| committed | on     | 1.000    | 0.983   | 0.302      |
| real      | off    | not run  | not run | not run    |
| real      | on     | not run  | not run | not run    |

Measured on 2026-11-20 with `EMBED_CACHE_DIR=<cache> pytest tests/rag -s` (89 passed, 1 skipped) on an AMD Ryzen 9 PRO 8945HS w/ Radeon 780M Graphics. Off-topic questions were rejected 6/6 in both configurations. The only per-question difference is q28 ("Why does a thermos flask keep drinks hot?"), which moves from HIT@2 to HIT@1 with the reranker; q25 is HIT@2 in both. The real set was not run: there are no real pages yet.

Decision: `RERANK_ENABLED` defaults to off because recall@6 is equal (1.000 both ways), so the rule is not met. MRR rises from 0.950 to 0.983 at 0.30 s/question, so turning it on later is a judgement call for the owner. If the reranker ever improves recall@6 within 1.5 s per question, `test_rerank_default_matches_eval` fails and the default must be turned on.

Re-run and update this table when the embedding model, the reranker model or the corpus changes.
