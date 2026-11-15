# Learnmate — System design

## Overview
Learnmate is a daily study mentor for students in grades 5 to 10, run by their parent. The parent picks a subject and its school material (notes, PDFs, Word files, photos or a Google Classroom link), notes a session PIN and hands over the tablet. The student follows a short plan: a warm-up, a step-by-step lesson from a mentor that answers from their own books, and a test at the end, earning points, streaks and levels along the way. Only a parent can end the session, with the PIN. The parent gets every grade, every "left the app" alert and a session summary on Telegram.

## Stack
Native Android app plus a small Python server. The server is needed because the Telegram bot, the AI calls and the "left the app" watchdog must keep running when the tablet is closed. The server runs on the family's own always-on computer and is reached from the tablet through a Cloudflare Tunnel, so no rented server and no open ports are needed.

| Part | Choice | Reason |
|---|---|---|
| App language and UI | Kotlin 2.x, Jetpack Compose, Material 3 (themed with the UX tokens) | Native Android gives the best grip on lifecycle events, back-button blocking and later screen pinning |
| App navigation | Navigation Compose with two graphs (parent, session) | The session graph only contains S04-S08 and S11, so locked mode is enforced by the graph itself |
| App networking | Retrofit + OkHttp + kotlinx.serialization | Standard, well documented, easy to fake in tests |
| App local storage | Room (session cache, outbox of events), DataStore (appearance, server settings) | Session state and alerts must survive the app being killed mid-test |
| App background work | WorkManager for the outbox; a coroutine heartbeat while a session runs | Queued events are delivered when the network or the server comes back |
| App charts | Compose Canvas (bar, line, pie drawn by hand) | Three simple chart types do not justify a chart library |
| App DI | Manual constructor injection (one `AppContainer`) | Small app; no annotation processing to debug |
| Server language and framework | Python 3.12, FastAPI, Uvicorn | Python reads PDFs and Word files well and has the best AI and retrieval libraries |
| Storage | SQLite (WAL mode) via SQLAlchemy 2.0, Alembic migrations; uploaded files on disk under `data/files/` | One family, one writer: SQLite is plenty and backs up as one file |
| Retrieval (RAG) | Hybrid search scoped to the session's chapters: SQLite FTS5 (BM25) for keywords plus dense vectors, fused with reciprocal rank fusion | Keywords catch exact terms ("photosynthesis", "Article 21"); vectors catch paraphrased questions; fusing both is the standard, robust default |
| Embeddings | fastembed (ONNX, CPU) with `BAAI/bge-small-en-v1.5` (384 dimensions), run on the server | Free, private (the child's notes never leave the machine for indexing), fast enough on a normal CPU |
| Vector search | Vectors stored as float32 BLOBs in the `chunk` table; exact cosine search with numpy over the session's chunks only | A session covers a few hundred to a few thousand chunks, so exact search takes milliseconds; no vector database or SQLite extension to run |
| Document reading | pypdf (PDF text), pypdfium2 (render scanned pages), python-docx (Word), Pillow (images); scanned pages and photos read by the AI model's vision input | Covers typed and scanned school material without running Tesseract |
| AI | Anthropic Claude API through one `llm` module: `claude-sonnet-5-5` for lessons, mentor answers and test questions; `claude-haiku-4-5-20251001` for page reading, chapter detection and rewriting follow-up questions for search; the API's web search tool for "check outside the books" | Strong at grounded answers with citations, structured JSON output and vision; one module keeps the provider swappable and lets tests use a fake |
| Telegram | python-telegram-bot 21 with long polling, running inside the server process | Outbound only, so it works behind the tunnel; inline buttons for "New PIN" |
| Google Classroom | Google sign-in on the device (Authorization API, read-only Classroom and Drive scopes); the server uses the short-lived access token once to download the attached files | No Google secrets stored on the server; tokens are never persisted |
| Hosting | The family's own Linux computer, Docker Compose with two services: `server` and `cloudflared` (a named Cloudflare Tunnel to a fixed hostname on a domain in Cloudflare) | No monthly server bill; HTTPS and the public hostname come from Cloudflare; the computer opens no inbound ports |
| App-to-server auth | One long random device token in the server's `.env`, built into the app from `local.properties`, sent on every request over the tunnel's HTTPS | Private single-family use; no accounts to build |
| Backups | A nightly job inside the server container: SQLite online backup plus a copy of `data/files/` to a backup folder, keeping 14 days | The data lives on one home computer, so a disk failure must not lose grades and notes |
| Formatter (Kotlin) | ktlint via the `org.jlleitschuh.gradle.ktlint` Gradle plugin; `.editorconfig` ignores the function-naming rule for `@Composable` functions (Compose names functions in PascalCase) | Handbook default for Kotlin |
| Formatter (Python) | ruff (`ruff format` and `ruff check`, config in `server/pyproject.toml`) | Handbook default for Python |
| Formatter (Markdown, YAML, JSON) | Prettier, run on the repo's docs and CI files only (`.prettierignore` excludes `design/`, `android/`, `server/`) | Handbook default for Markdown and JSON |
| Tests | Server: pytest + httpx TestClient. App: JUnit 5 + Turbine for logic, Robolectric + Compose UI test for screens, Roborazzi for JVM screenshots | Everything runs on the JVM and in CI without an emulator |
| CI | GitHub Actions: one job for `server/`, one for `android/`, one for Prettier | Formatter checks and tests on every pull request |

Repository layout: `android/` (Gradle project, single `app` module with packages `ui/`, `session/`, `data/`, `domain/`), `server/` (package `learnmate`), `deploy/` (Compose file, `.env.example`, runbook), `design/` (owned by the designer).

## Components

**Android app**
- `ui/theme`: colours, type, spacing, shapes, shadows and glows from `ux.md`; light, dark and match-device.
- `ui/components`: buttons (primary gradient, secondary, ghost, split Send), cards and hero cards, stat tile, step row, progress bar, chips, subject tile, library row, answer option, PIN dots and keypad, password field, alert, Telegram line, toggle, segmented control, side nav, light/dark switch, dialog, session pill, chat bubbles and the visual block.
- Parent graph: S01 Parent home (and first run), S02 Today's material, S03 Hand over, S09 Settings.
- Session graph: S04 Session home, S05 Mentor, S06 Test, S07 Test result, S08 End session, S11 Session locked. The system back button is consumed in this graph; leaving it requires the end of the session to be recorded.
- `session/Presence`: observes `ProcessLifecycleOwner` (ON_STOP = left, ON_START = back), sends a heartbeat every 15 s while a session runs, and writes every event to the outbox first.
- `session/Inactivity`: a pure timer fed by every touch and key event on S04-S07; warning at 4 min, lock at 5 min (values from server settings).
- `domain/`: pure Kotlin for PIN-pad state, lockout display, grade bands, plan step state, so it can be unit tested without Android.
- `data/`: Retrofit API, Room database (cached current session, test progress, outbox), repositories. The server URL is the tunnel hostname, set in `local.properties`.

**Server**
- `api/`: REST endpoints under `/api/v1` for family, subjects, materials, sessions, plan, mentor, tests, exams, settings. Every request needs the device token.
- `ingest/`: stores uploads, extracts text per page, sends scanned pages and photos to the vision model, detects chapters, cuts chunks and hands them to `rag/` for indexing; finds figures in page images and saves crops with a description.
- `rag/`: everything about finding the right passages.
  - Chunking: split on headings first, then paragraphs, into chunks of about 800 characters with about 120 characters of overlap; a chunk never crosses a chapter boundary; each chunk keeps material, chapter and page.
  - Indexing: each chunk is indexed in FTS5 and embedded. The embedded text is prefixed with "<subject> / <material title> / <chapter>" so short chunks keep their context. Figure descriptions are indexed as chunks of kind `figure`, so a question can find a picture.
  - Scope: every search takes a scope (the session's chapter ids, or its material ids when no chapters were named) and only ever looks at chunks inside it. Nothing from other subjects or materials can be retrieved.
  - Query: for a follow-up ("why does that happen?"), Haiku rewrites the question and the last few turns into a standalone search query; the first question of a turn is used as it is.
  - Search: BM25 top 20 and vector top 20 inside the scope, fused with reciprocal rank fusion (k = 60), then neighbouring chunks of the top hits are merged so a passage isn't cut mid-explanation; the top 6 passages (about 5,000 characters) go to the model.
  - Relevance floor: if the best vector similarity is below a threshold (tuned on the eval set, starting at 0.35) and BM25 finds nothing, the mentor answers "the books don't cover this" without calling the model.
  - Eval: a fixture set of invented chapters with 30 questions and their expected chunks; `pytest` fails if recall@6 drops below 0.85. Retrieval changes are judged against it, not by feel.
- `classroom/`: given a Classroom link and an access token, downloads the attached Drive files and hands them to `ingest/`.
- `sessions/`: session lifecycle and the rules: PIN creation and replacement, wrong-PIN and fallback lockouts, resend rate limit, inactivity locks, study time (locked minutes excluded), summary.
- `presence/`: records heartbeats and app events; a watchdog task checks every 10 s and treats a running session with no heartbeat for 45 s as "left Learnmate" (covers a killed app or a dead tablet).
- `plan/`: pure functions for today's plan (warm-up, lesson, test; weekly test on the first session of an ISO week; surprise test in the 7 days before an exam date), points, streaks and levels.
- `mentor/`: lesson building and answers on top of `rag/`; books-only answers must cite passage ids from the retrieved set, which the server validates; the outside-the-books path; validation of the visual block JSON.
- `tests/`: question generation from the scoped chunks (each question tied to a chunk), deterministic grading, grade bands, missed tests.
- `telegram/`: the bot (connect with `/start <code>`, "New PIN" inline button), message templates, a send queue in the database with retries so a message is never lost when Telegram is down.
- `llm/`: the only module that talks to the AI provider; a fake implementation for tests.
- `backup/`: the nightly backup job and its retention.

## Data model
SQLite, one family per server.

- `family`: child_name, grade, telegram_chat_id, telegram_link_code, fallback_hash (argon2id), fallback_wrong, fallback_locked_until, outside_books_allowed (default true), inactivity_warn_s (240), inactivity_lock_s (300), created_at.
- `subject`: id, name, icon, created_at.
- `material`: id, subject_id, title, kind (`upload` | `classroom`), source_url, status (`reading` | `ready` | `failed`), error, pages_total, pages_read, chapters_hint, created_at.
- `material_file`: id, material_id, path, mime, size.
- `chapter`: id, material_id, name, position.
- `chunk`: id, material_id, chapter_id, page, position, kind (`text` | `figure`), figure_id, text, embedding (BLOB, 384 float32, normalised), embed_model; `chunk_fts` FTS5 table over text.
- `figure`: id, material_id, chapter_id, page, path (cropped PNG), description.
- `exam`: id, subject_id, date.
- `session`: id, subject_id, type (`learn` | `recap` | `test_only`), question_count, state (`set_up` | `running` | `locked` | `ended` | `force_ended` | `cancelled`), pin_hash, pin_enc (encrypted with the server's PIN key, for resending), pin_version, pin_last_sent_at, wrong_pins, pin_locked_until, created_at, started_at, ended_at, end_reason (`pin` | `fallback`), study_seconds, plan_json (steps and their status).
- `session_material` / `session_chapter`: the material and chapters the session covers; together they are the retrieval scope.
- `session_event`: id, session_id, type (`started`, `left`, `back`, `heartbeat_lost`, `warned`, `locked`, `unlocked`, `wrong_pin`, `pin_locked`, `pin_resent`, `pin_replaced`, `fallback_wrong`, `ended`), at, data_json.
- `heartbeat`: session_id, last_at (one row per session).
- `message`: id, session_id, role (`mentor` | `student`), text, sources_json (chunk ids, material title, chapter, page), visual_json, outside (bool), outside_source_url, retrieval_json (query used, chunk ids and scores, for spot checks), created_at.
- `test`: id, session_id, subject_id, kind (`warmup` | `daily` | `weekly` | `surprise` | `test_only`), status (`in_progress` | `done` | `missed`), current_index, score_pct, band, created_at, finished_at.
- `question`: id, test_id, position, prompt, options_json (4), correct_index, explanation, chunk_id, answer_index, answered_at.
- `points`: id, session_id, reason (`warmup`, `quick_check`, `test`, `streak`), amount, at.
- `outbox` (server, Telegram): id, text, buttons_json, status, attempts, next_try_at.

Device (Room): `current_session` (id, state, PIN hash and version for offline checks, step, test progress), `event_outbox` (type, at, sent).

Levels, streaks and totals are computed from `points` and `session`, not stored. Deleting a subject deletes its material, files, chapters, chunks (with their vectors) and figures and keeps tests and grades. "Delete all" removes every row and file except `family`. Changing the embedding model re-embeds every chunk on start-up (`embed_model` marks stale rows).

## Key flows

**1. Set up and start a session (S01 -> S02 -> S03 -> S04)**
1. S02 loads subjects with material counts and latest grades (`GET /subjects`). New uploads go to `POST /subjects/{id}/materials`; the server stores the files, answers `reading`, and ingests in a background task (read pages, detect chapters, chunk, embed, index); S02 polls `GET /materials/{id}` for `pages_read` until `ready` or `failed`.
2. Continue calls `POST /sessions` with subject, type, material or chapter ids and question count. The server creates the session in `set_up`, records its scope, makes a random 4-digit PIN (`secrets.randbelow`), stores its hash and encrypted copy and sends it to Telegram with a "New PIN" button. Any older `set_up` session is cancelled.
3. S03 shows the PIN returned by that call (the only time the device receives the PIN in clear). "Make a new PIN" calls `POST /sessions/{id}/pin`, which bumps `pin_version` and sends the new PIN.
4. "Start session and hand over" calls `POST /sessions/{id}/start` (state `running`, Telegram "session started"). The app stores the session and the PIN hash in Room and switches to the session graph; S04 shows the plan from `GET /sessions/{id}/plan`.

**2. Lesson, mentor answers, test and grade (S04 -> S05 -> S06 -> S07)**
1. The lesson starts with `POST /sessions/{id}/mentor/lesson`: the server takes the scoped chunks in chapter and page order (for a long chapter, the passages retrieved for the chapter's own headings) and asks the model for a step-by-step lesson for the S05 step panel, each step with a quick check and the passage ids it came from.
2. A student question (`POST /sessions/{id}/mentor/messages`, `mode=books`): the server builds the search query (rewritten if it's a follow-up), runs hybrid search inside the session's scope, and either stops at the relevance floor ("the books don't cover this", `can_check_outside=true`) or sends the top passages to the model. The model must answer in JSON citing passage ids, with an optional visual (`chart`, `steps`, `table` or `figure` by id). The server checks every cited id is in the retrieved set; if not, it retries once and then falls back to "the books don't cover this". The source line shows material, chapter and page of the cited passages. `mode=outside` (only when the setting allows it) uses the web search tool and is stored with `outside=true` and its source URL.
3. The test is generated when the lesson finishes (`POST /sessions/{id}/tests`): 4-option questions spread across the scoped chapters, each tied to a chunk. Each answer is posted as it is given, so a closed app resumes at `current_index`.
4. The last answer finishes the test: the server grades it, writes points, queues the Telegram grade (target under a minute) and S07 shows score, band and points.

**3. Leaving the app, inactivity and ending (S08, S11)**
1. Presence: ON_STOP writes a `left` event to the outbox and posts it at once; the server queues "<child name> left Learnmate during the session (<time>)". ON_START sends `back`. If the device goes silent for 45 s, the watchdog sends the same alert itself.
2. Inactivity: at 4 min the app shows the S11 warning; at 5 min it posts `locked` (Telegram) and shows the S11 lock. Unlock uses the same PIN check as ending; locked minutes are excluded from `study_seconds`.
3. Ending: S08 posts the 4 digits to `POST /sessions/{id}/end`. The server checks the current PIN version, counts wrong tries (3 reveals the fallback link, 5 locks the pad for 15 min and tells Telegram) and on success ends the session, writes `missed` for an unfinished test, builds the summary and sends it to Telegram. "Forgot the PIN" decrypts `pin_enc` and resends the same PIN, at most once a minute.
4. Fallback: `POST /sessions/{id}/force-end` with the password, checked against the argon2id hash; 3 wrong tries lock it for 1 hour. If the server is unreachable (computer asleep, home internet down), the app checks the password against a hash cached in DataStore, ends locally and syncs the force-end through the outbox. PIN checks offline use the cached PIN hash for the latest version the app has seen (a PIN replaced from Telegram while offline can't be known on the device).

**4. Hosting through the tunnel**
1. One-time: create a named tunnel in the Cloudflare dashboard with a public hostname (for example `learnmate-api.<your domain>`) pointing at `http://server:8000`; put the tunnel token, the device token, the Anthropic key and the Telegram bot token in `deploy/.env`.
2. `docker compose up -d` in `deploy/` starts `server` (no published ports) and `cloudflared`; both restart automatically after a reboot.
3. The app is built with the hostname and device token in `local.properties`. Telegram uses long polling, so nothing else has to reach the computer.
4. The computer must stay awake while a session runs; the runbook in `deploy/README.md` covers turning off sleep, checking the tunnel, and restoring from a backup.

## Testing approach
- Server, from `server/`: `ruff format --check . && ruff check . && pytest`. The `llm` fake returns fixed lessons, answers and questions; Telegram is a recording fake; time is injected so lockouts, the watchdog and streaks are tested without waiting. Sample PDF, Word and image files with invented content live in `server/tests/fixtures/`.
- Retrieval: `pytest tests/rag` runs the eval set with the real embedding model (cached in CI) and fails below recall@6 of 0.85; scope tests prove a search never returns chunks from outside the session's chapters or materials.
- App, from `android/`: `./gradlew ktlintCheck testDebugUnitTest`. Pure domain tests (PIN pad, lockouts, inactivity timer, grade bands), repository tests against a fake API, and Robolectric Compose tests per screen. `./gradlew verifyRoborazziDebug` compares screenshots of each built screen (light and dark, 1280x800) with recorded ones; `./gradlew recordRoborazziDebug` refreshes them for the designer's review.
- Repo docs and CI files: `npx prettier --check .`
- Deploy: `docker compose -f deploy/compose.yaml config` in CI; by hand, `curl https://<hostname>/api/v1/health` returns 200 through the tunnel.
- End to end, by hand on a tablet: start a session, ask the mentor a question answered in the notes and one that isn't, leave the app, wait for the inactivity lock, finish the test, end with a wrong then right PIN, and check every Telegram message arrives within a minute.

## Open questions
- Material language: the embedding model is English. If school material is in another language (or mixed), switch to a multilingual model (`intfloat/multilingual-e5-small` class) before `rag-embed` is built; later it is one setting plus a re-embed.
- The tunnel needs a domain whose DNS is on Cloudflare (a free plan is enough); a temporary `trycloudflare.com` address changes on every restart and can't be built into the app.
- If the home computer sleeps or loses internet during a session, Telegram alerts arrive late (when it's back) and the tablet ends sessions with its offline checks. Screen pinning (Android lock task mode) would make leaving the app much harder; it fits as a later ticket.
- AI usage and cost: Sonnet for lessons, answers and tests is roughly a few dollars a month for one student at one session a day; embeddings cost nothing; a monthly budget cap is not set yet.
- Google Classroom links depend on the school allowing third-party access for the student account; the fallback (upload the file) is already in S02's error state.
