---
id: S06
name: Test
purpose: Answer the session's test questions
size: 1280x800
---

## Content and actions
- Test type chip and session pill in the top bar.
- "Question 3 of 5", points so far, progress bar.
- Question card with four options as large buttons in a 2x2 grid (one column on phones). One tap selects; selected shows a blue border and a filled letter.
- "Check answer" shows feedback, then "Next question". After the last question it goes to S07.
- No mentor and no back link during a test.

## States
- Main (screen.html): an option selected. Dark (states/dark.html).
- Feedback (states/feedback.html): the right answer outlined green with "Correct!"; a wrong pick red with "Your answer"; a kind explanation with the source page.
- If the app is closed mid-test, the test resumes at the same question when reopened; the parent alert still goes out.

## Notes and open questions
- Daily test 5 questions, weekly 15, surprise 8; test only 5, 10 or 15 as chosen on S02 (chip "Test only"; the S07 Telegram message names it a test-only session). Multiple choice only in the MVP.

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first layout (2x2 answers) and dark mode. Requested in UX review.
- Test-only length and chip noted. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
