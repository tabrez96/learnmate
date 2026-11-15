# Learnmate
## Problem
Students in grades 5-10 have school material scattered across notes, documents and Google Classroom, with no daily revision plan and no feedback loop. Parents want proof that revision happens and want to control the session. Evidence: this is the owner's first-hand problem, taken as given; no external demand data has been gathered. Peer products (plan + quiz + AI tutor) exist, which shows the category is real: e.g. https://www.mentorastudy.com/, https://www.mentora.cloud/.

## Users & buyer
- Student (grade 5-10): studies in a session, does the mentor lesson, tests, earns points.
- Parent: sets up the account, starts and ends sessions, receives grades and alerts on Telegram. Parent is also the buyer.
- First deployment is private use (own family); no public launch assumed.

## Competition
Many AI study apps do syllabus upload, plan, flashcards and quizzes. Gaps we target: a parent-controlled loop (PIN-locked session, Telegram alerts when the student leaves the app, grades pushed after each test) and answers restricted to uploaded syllabus material by default. Generic tutors answer from the open web and have no parent session control.

## MVP scope
- Upload school notes/documents/syllabus (optional in advance). Each day needs a document upload or a Google Classroom link; if neither is given, the student picks an earlier syllabus to recap with a test. Students may name chapters.
- Daily plan following the syllabus and school schedule.
- Text mentor teaching the day's topic step by step, answering only from uploaded material; external-resources toggle, off by default.
- Gamification: points, streaks, levels, short challenges.
- Assessments: small daily test, weekly test, random tests around exam dates (exam calendar entered manually). Every session ends with a small test.
- Telegram to parent: grade after each test; alert if the app closes, backgrounds or exits during a session.
- Sessions: parent starts and hands over the device; only a parent can end it with a PIN; forgotten PIN is sent via Telegram.
- Defaults chosen for private use (adjustable): PIN 4 digits, 5 wrong attempts then 15-minute lockout, Telegram-sent PIN valid 10 minutes and single use; grading as percentage with A-F bands; a missed daily test is recorded as "missed" (not zero); uploaded material and results kept until the parent deletes them; daily source is prompted, not enforced.

## Out of scope
- Voice mentor.
- Exam calendar import from Google Classroom.
- Public launch concerns (multi-school curricula, formal COPPA/GDPR-K compliance, payments).
- Other parent channels besides Telegram.
- Teacher accounts.

## Pricing hypothesis
Not a priority while private. If opened up: a family subscription (roughly 5-10 USD/month, unvalidated), with a free tier limited to a few uploads per week. Treat as a hypothesis only.

## Success metrics
- Study sessions completed per week per student; days with a completed session (streak length).
- Share of sessions ending with a test.
- Parent receives the Telegram grade within a minute of a test finishing.
- Share of mentor answers traceable to uploaded material (spot-checked).
- Parent says they trust the "it happened" proof (qualitative).

## Risks
- Name: "Learnmate" has not been checked. No web search was available when this brief was written, so availability on app stores, domains and trademark registers is unknown. The name is two common words and is likely to be in use somewhere. Fine for private use; run a name and trademark check before any public release.
- A web app cannot reliably detect that it was closed or backgrounded; the detection method (e.g. heartbeat, visibility events) will limit how trustworthy alerts are. A child can also leave the device screen without closing the app.
- Syllabus-only answers depend on document quality (scans, handwriting, OCR errors) and risk hallucination.
- Google Classroom access needs OAuth and may be restricted for school-managed accounts.
- Minors' data: even privately, keep storage minimal and deletable.
- Crowded category; the parent-control loop must be the visible difference.

## Runner-up ideas
Not applicable: this is the owner's own idea, so no alternatives were researched.
