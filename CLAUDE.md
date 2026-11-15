# Learnmate

A parent-supervised daily study mentor that teaches from your school syllabus and reports every test

Students in grades 5-10 have school material scattered across notes, documents and Google Classroom, with no daily revision plan and no feedback loop. Parents want proof that revision happens and want to control the session. Evidence: this is the owner's first-hand problem, taken as given; no external demand data has been gathered. Peer products (plan + quiz + AI tutor) exist, which shows the category is real: e.g. https://www.mentorastudy.com/, https://www.mentora.cloud/.

## Where things are
- `design/` is the design library: `brief.md`, `ux.md`, and `screens/S01-name/` (`screen.png` + `spec.md`, plus
  `states/*.png` for empty, error and other states). Screens have permanent IDs (S01, S02, ...). Tickets name the
  screens they build by ID. **Read the spec and look at the screenshot of every screen you build**; `ux.md` has the
  colors, type and spacing. Don't edit `design/`; the designer owns it.
- Design canvas (private and behind a login, so you can't open it; it's where the design gets reviewed): <!-- canvas -->not published yet<!-- /canvas -->
- Source code lives outside `design/`. Put it where the stack below says.

## Stack
<!-- stack -->
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
<!-- /stack -->

## How we work here
- Two long-lived branches: `develop` is where the work lands (every ticket's PR goes there); `master` is the
  release branch and only moves when the maintainer launches a release. Never commit to `master`.
- One ticket at a time, on its own branch (`dmi/t-<n>`), cut from `develop`. Small, focused changes.
- Each ticket becomes a pull request into `develop` that the maintainer reviews. A pull request changes **under 500
  lines** (code and tests; lockfiles and generated files don't count); anything bigger can't be reviewed, so split it
  into more tickets.
- Commit messages and pull request titles say only what the change does (`Show the running meeting under Now`): no
  ticket number and no product name.
- Prefer boring, proven tools. Don't add a dependency unless the ticket needs it.
- Keep platform-specific code thin and put logic in pure code with unit tests (aim for about 90% coverage). Code
  that can't run in the sandbox is verified by review plus those tests, and then by hand by the maintainer.
- Format with the formatter in the stack table before you say you're done, and keep its check in CI and next to the
  test commands. Never format files your change doesn't touch.
- Write tests for what you build, and run them before you say you're done. Document the build and test commands in the README under "Development".
- Never commit secrets, tokens or personal data. Don't put real credentials in examples.
- If the ticket is unclear or the design is missing something, ask the architect or designer instead of guessing.
