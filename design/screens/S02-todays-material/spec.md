---
id: S02
name: Today's material
purpose: Choose what the student learns today: a subject, then its material, something new, or a recap
size: 1280x800
---

## Content and actions
- Session type (top right, segmented control): "Learn and test" (default: lesson, then test) or "Test only" (test-only state).
- 1. Subject: one row of subject tiles (radio group, one subject per session). Each tile shows an icon, the subject name, how many materials it holds and its latest grade ("Nothing yet" when empty). The subject from today's plan is pre-selected. "+ New subject" opens the add-subject dialog (name only, same as S09).
- 2. "<Subject> material" (left): the materials in the picked subject, newest first. Each row is a checkbox (file type, name, date added, last result chip; "New" if never tested). Several can be selected. Changing the subject clears the selection.
- "Add new <Subject> material" (right): upload area (photo, PDF or Word, several files; each file becomes a row with Reading... / Ready / Couldn't read), Google Classroom link field (Google sign-in the first time), and "Chapters to focus on" (optional, free text). New material is saved under the picked subject and pre-selected.
- "Continue" goes to S03. Enabled when a subject is picked and at least one of its materials is selected, a new file is Ready, or a Classroom link is accepted.
- "Nothing new today: recap an earlier chapter" opens the recap state.
- Back returns to S01.

## States
- Main (screen.html): Science picked, one Science material selected, chapter named. Dark (states/dark.html).
- Recap (states/recap.html, dark twin states/recap-dark.html): the subject row, then that subject's earlier chapters with the material they come from and the last result; one selected; a suggestion for the weakest chapter in the subject; Continue goes to S03 with a recap lesson and test.
- Test only (states/test-only.html, dark twin states/test-only-dark.html): the subject row, then the chapters of the subject's materials, grouped under each material, as checkboxes with the last result; question count 5 / 10 / 15 (default 10); "Today will be" summary. Continue is enabled when at least one chapter is picked and goes to S03.
- Error (states/error.html): unreadable photo with a plain fix, and Classroom sign-in blocked with the fallback (upload the file).
- Loading: file row shows "Reading... 2 of 4 pages" with a progress bar.
- Empty subject: the left column says "No Science material yet. Add some on the right." In Test only and Recap it says "Nothing to test in Science yet" with a link to Learn and test.
- No subjects (first day): the subject row shows only "+ New subject", the material columns are hidden and the recap link is hidden.

## Notes and open questions
- The subject is the entry point for sessions and tests; material always belongs to exactly one subject.
- One subject per session keeps the lesson, the test and the Telegram grade about one thing.
- The daily source is prompted, not enforced: the parent can always choose recap instead.
- Done by the parent before handing over; the student never sees upload controls during a session.
- Six tiles fit in one row on the tablet; with more subjects the row scrolls sideways. On phones the tiles wrap into two columns.

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first two-column layout, dark mode, and "From your library" to pick existing material. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- Session type control (Learn and test / Test only) and test-only state for selected chapters. Requested in UX review.
- Subject first: a subject row (single choice) above the material, which now lists only that subject's material; recap and test only also start from the subject; dark twins added for recap and test only. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
