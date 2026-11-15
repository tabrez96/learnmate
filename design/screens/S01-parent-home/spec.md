---
id: S01
name: Parent home
purpose: See whether today's study happened and start a session
size: 1280x800
---

## Content and actions
- Top bar (every screen): logo, light/dark switch (sun and moon), "Settings" (S09).
- Greeting, child name, grade and level.
- Four stats: streak (days with a completed session), sessions this week, average grade this week, points.
- Today card (gradient hero): "What is Omar studying today?", a status chip (No session yet / Done), a line saying the subject and material are chosen next (new notes, a Classroom link, earlier material, a recap or a test), and "Start today's session", which leads to S02. It names no chapter or topic: nothing is known about today until material is picked or added on S02.
- Recent tests: each test with type, topic, time and grade chip (percentage plus A-F band). A missed daily test shows a grey "Missed" chip, never 0%. "All results" opens the full list (same rows, scrolling; no separate screen in the MVP).
- Right column: exam reminder when an exam is within 14 days ("Edit" goes to S09 Exam dates), and the Telegram line.

## States
- Main (screen.html): a child with history, no session yet today.
- Dark (states/dark.html): the same screen in dark mode.
- First run (states/first-run.html): three steps (child name and grade, connect Telegram, choose a fallback password of at least 8 characters, typed twice) and a panel explaining how sessions are locked. There is no PIN to set: Learnmate makes one for every session. "Finish setup" stays disabled until Telegram is connected and the fallback password is set. After setup the app opens S01.
- Done today: Today chip reads "Done, 80% B" and the button becomes "Start another session" (secondary style).
- Loading: card outlines with grey blocks; no spinner over the whole page.
- Error (cannot load results): inline alert in the Recent tests card with "Try again".

## Notes and open questions
- Grade bands: A 90-100, B 80-89, C 70-79, D 60-69, E 50-59, F below 50.
- One child per account in the MVP.
- Tablet layout: two columns (main 1.55 : side 1). Below 720 px wide the columns stack.

## Change log
- Created for the first UX of the MVP brief.
- Redesigned tablet-first (1280x800) with a dark mode; PIN setup removed from first run (the PIN is now daily, see S10); Today's PIN card added. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- Today's PIN card replaced by a Session PIN note (PIN is per session); first run gains a fallback password step and goes to S01, not S10; Telegram handle sample fixed. Requested in UX review.
- Session PIN card removed from the right column; the PIN is only shown on S10 and sent to Telegram. Requested in UX review.
- Today card no longer names a chapter before any material is picked; it asks what is being studied and points to S02. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
