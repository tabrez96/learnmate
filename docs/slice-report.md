# Slice report

## Purpose

Run one real chapter through the whole learn path on a tablet: upload, page reading, lesson and questions in S05.
Retrieval problems found here become tickets before the remaining screens are built.

## Setup

1. On the computer, start the server with `ANTHROPIC_API_KEY`, `DEVICE_TOKEN` and `EMBED_CACHE_DIR` set:
   `uvicorn learnmate.main:create_app --factory --host 0.0.0.0`.
2. In `android/local.properties` set `learnmate.serverUrl=http://<computer LAN IP>:8000` and `learnmate.deviceToken`.
3. Put the tablet on the same Wi-Fi and run `cd android && ./gradlew installDebug`.
4. Copy one chapter file from `server/data/eval/real/` to the tablet.

## Procedure

1. Write the 10 questions first in the Questions table, with their expected page: 6 answered in the chapter (each with
   the page that answers it) and 4 not in the chapter.
2. Open "Slice run", enter the subject name, pick the file and tap "Upload and start".
3. In S05 read every step and answer its quick check.
4. Ask the 10 questions in order, typed exactly as written. Do not tap "Check outside the books".
5. Press back, tap "Record AI cost" and copy the log into this file.
6. For page reading detail, run on the computer:
   `sqlite3 data/learnmate.db "SELECT purpose, model, count(*), round(sum(cost_usd), 4) FROM llm_usage WHERE at >= '<run start, UTC>' GROUP BY purpose, model;"`
   and
   `sqlite3 data/learnmate.db "SELECT page, length(text) FROM material_page WHERE material_id = <id> ORDER BY page;"`.
   A page read through the vision model shows up as one page-reading usage row.
7. Fill in Verdict and Likely cause for every question.
8. Tap "End current session".

## Material

- File: Not run yet
- Pages read: Not run yet
- Chapters found: Not run yet
- Time to ready: Not run yet

## How the pages were read

| Page        | Read as (text / vision) | Characters  | Notes       |
| ----------- | ----------------------- | ----------- | ----------- |
| Not run yet | Not run yet             | Not run yet | Not run yet |

## Lesson

Generated in: Not run yet

| Step        | Title       | Sources     |
| ----------- | ----------- | ----------- |
| Not run yet | Not run yet | Not run yet |

## Questions

| #           | Question    | Answer source | Time (s)    | Expected    | Verdict     | Likely cause |
| ----------- | ----------- | ------------- | ----------- | ----------- | ----------- | ------------ |
| Not run yet | Not run yet | Not run yet   | Not run yet | Not run yet | Not run yet | Not run yet  |

## AI cost

- Spent before: Not run yet
- Spent after: Not run yet
- This run: Not run yet

## Verdicts

- `right source`: answered from the books and the cited page is the expected page, or the chunk starting on the page before it.
- `wrong source`: answered, but from the wrong page or the wrong material.
- `missed`: refused, but the chapter has the answer.
- `correctly refused`: not in the chapter and refused.
- `wrongly answered`: not in the chapter, but answered from the books.

## Likely causes

- `reading`: the page text is wrong or missing (check `material_page`).
- `chunking`: the answer is split across chunks or cut off.
- `search`: the right chunk exists but is not in the top 6, or the relevance floor rejected it.
- `prompt`: the right passage was retrieved but the answer ignored it, cited the wrong one, or answered without it.

## Problems found

Every `wrong source`, `missed` and `wrongly answered` row goes here.

| Question    | Verdict     | Likely cause | Evidence    | Follow-up ticket |
| ----------- | ----------- | ------------ | ----------- | ---------------- |
| Not run yet | Not run yet | Not run yet  | Not run yet | Not run yet      |

## Notes

- The app sends no heartbeat yet, so the server queues one "left the app" Telegram alert during the run. That is
  expected.
- The real chapter file and the database stay on the computer and never go into git.
