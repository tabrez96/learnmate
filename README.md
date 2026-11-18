<!-- about -->

# Learnmate

**A parent-supervised daily study mentor that teaches from your school syllabus and reports every test**

## Screens

### S01 · Parent home

See whether today's study happened and start a session

![S01 Parent home](design/screens/S01-parent-home/screen.png)

### S02 · Todays Material

![S02 Todays Material](design/screens/S02-todays-material/screen.png)

### S03 · Hand over

Confirm the session, note the session PIN and hand the device over

![S03 Hand over](design/screens/S03-hand-over/screen.png)

### S04 · Session home

The student sees today's plan and their progress, and continues

![S04 Session home](design/screens/S04-session-home/screen.png)

### S05 · Mentor

Learn today's topic step by step and ask questions

![S05 Mentor](design/screens/S05-mentor/screen.png)

### S06 · Test

Answer the session's test questions

![S06 Test](design/screens/S06-test/screen.png)

### S07 · Test result

See the score, what to review and the rewards earned

![S07 Test result](design/screens/S07-test-result/screen.png)

### S08 · End session (parent PIN)

A parent ends the session with the session PIN, or force-ends it with the fallback password as a last resort

![S08 End session (parent PIN)](design/screens/S08-end-session-pin/screen.png)

### S09 · Settings

Manage appearance, Telegram, the PIN and fallback password, subjects and their material, exam dates and the mentor

![S09 Settings](design/screens/S09-settings/screen.png)

### S11 · Session locked

Lock the session after 5 minutes with no activity, until a parent unlocks it with the session PIN

![S11 Session locked](design/screens/S11-session-locked/screen.png)

<!-- /about -->

## Development

### Server (`server/`)

Needs Python 3.14.

```sh
cd server
python3.14 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
alembic upgrade head                                    # migrate
uvicorn learnmate.main:create_app --factory --reload   # run
pytest                                                  # test
pytest tests/ingest --real                              # read real pages under data/eval/real/ with the real model (needs ANTHROPIC_API_KEY); output in data/eval/real/out/
python tests/ingest/make_fixtures.py                    # regenerate the ingest fixtures
# API calls need the header `Authorization: Bearer <DEVICE_TOKEN>` (only `/api/v1/health` is open)
ruff format . && ruff check --fix .                     # format
ruff format --check . && ruff check .                   # check
```

The database is `learnmate.db` in `DATA_DIR`.

Settings come from the environment:

| Variable                 | Meaning                                                | Default                     |
| ------------------------ | ------------------------------------------------------ | --------------------------- |
| `DATA_DIR`               | Where the database and files are kept                  | `data`                      |
| `DEVICE_TOKEN`           | Token the app sends on every request                   | empty                       |
| `MODEL_MAIN`             | Model for lessons, answers and tests                   | `claude-sonnet-5-5`         |
| `MODEL_FAST`             | Model for page reading and rewriting                   | `claude-haiku-4-5-20251001` |
| `ANTHROPIC_API_KEY`      | Key for the AI provider                                | empty                       |
| `LLM_PROVIDER`           | `anthropic`, or `fake` for offline runs                | `anthropic`                 |
| `EMBED_MODEL`            | Embedding model                                        | `BAAI/bge-small-en-v1.5`    |
| `RERANK_ENABLED`         | Turn on result re-ranking                              | `false`                     |
| `LLM_MONTHLY_BUDGET_USD` | Monthly AI spending cap                                | `10`                        |
| `LLM_PRICES`             | USD per million input/output tokens per model, as JSON | Sonnet 3/15, Haiku 1/5      |
| `LLM_WEB_SEARCH_USD`     | Price of one web search                                | `0.01`                      |

The Telegram bot only starts when `TELEGRAM_BOT_TOKEN` is set (messages wait in the outbox until then); tests never need it. Times in messages use `TIMEZONE` (an IANA name, default `UTC`). The month for the AI budget follows `TIMEZONE`; alerts go to Telegram at 80% and 100%, once each per month.

Every product default in `server/learnmate/config.py` (PIN rules, lockouts, inactivity limits, grade bands) can be overridden by its upper-cased name, e.g. `PIN_LENGTH=6`.

### Android (`android/`)

Needs JDK 17 and the Android SDK.

```sh
cd android
./gradlew assembleDebug                 # build
./gradlew testDebugUnitTest             # test
./gradlew ktlintFormat                  # format
./gradlew ktlintCheck                   # check
./gradlew recordRoborazziDebug          # record screenshots
./gradlew verifyRoborazziDebug          # verify screenshots
```

Screenshots are stored in `app/src/test/screenshots`.

#### Classroom check (debug builds only)

A debug-only screen that checks whether a Google account can grant read-only Classroom and Drive access. Add your Android OAuth client id to `android/local.properties`:

```
google.androidClientId=<your Android OAuth client id>
```

See `docs/classroom-check.md` for the procedure and results.

### Docs (repo root)

```sh
npm install
npx prettier --write .   # format
npx prettier --check .   # check
```

### CI

GitHub Actions runs three jobs on every pull request: `server`, `android` and `prettier`.

---

<sub>Created with ❤️ by Dunder Mifflin agents</sub>
