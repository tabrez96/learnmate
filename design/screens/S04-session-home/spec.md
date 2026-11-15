---
id: S04
name: Session home
purpose: The student sees today's plan and their progress, and continues
size: 1280x800
---

## Content and actions
- Top bar: logo, light/dark switch, session pill (lock icon and elapsed minutes; on every student screen).
- Left: greeting and today's topic on the gradient hero with the level bar; stats (streak, points, badges); a short challenge card.
- Right: Today's plan: warm-up challenge, mentor lesson (S05), daily test (S06). Done steps show a green check and points; the current step is outlined. The test is always the last step and cannot be skipped.
- Primary button continues the current step.
- "I'm done: ask a parent to end" opens S08. If the test isn't done yet, S08 notes "The daily test isn't finished; it will be recorded as missed."

## States
- Main (screen.html): warm-up done, lesson next. Dark (states/dark.html).
- Surprise test (states/surprise-test.html): in the 7 days before an exam date, a session can replace the daily test with an 8-question exam test at double points.
- Weekly test: on the first session of the week the plan gains "Weekly test, 15 questions" after the lesson.
- Test only (states/test-only.html): "Test only" chip, plan is warm-up then the test (no lesson, no mentor step); primary button "Start the test" goes to S06.
- Recap day: the lesson step reads "Recap: Fractions and decimals".
- Inactivity: on any student screen, 4 minutes without a touch or key shows the S11 warning; at 5 minutes the session locks (S11).

## Notes and open questions
- Points: warm-up correct answer +10, mentor quick check +10, test up to +100 (20 per correct answer), streak bonus +10 per streak day up to +50.
- Levels every 200 points with friendly titles (Starter, Learner, Explorer, Scholar, Expert...).

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first two-column layout and dark mode. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- Test-only state added. Requested in UX review.
- Points to the inactivity warning and lock on S11. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
