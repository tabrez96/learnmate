---
id: S07
name: Test result
purpose: See the score, what to review and the rewards earned
size: 1280x800
---

## Content and actions
- Left: score as a big gradient percentage, band chip with right-answer count, points, streak and level.
- Right: "One to review" (each wrong answer with the right answer and source page), new badge card when earned, Telegram line (grade sent to the parent).
- "Finish: ask a parent to end" goes to S08. "Keep studying: bonus challenge" adds 3 extra questions for points (not graded).

## States
- Main (screen.html): 80% B, grade sent. Dark (states/dark.html).
- Telegram unreachable (states/telegram-offline.html): grade saved, sending retries automatically.
- All correct: "One to review" becomes "Perfect score!".

## Notes and open questions
- Telegram message: "Omar finished the daily test on Photosynthesis: 80% (B), 4 of 5. Studied 28 min."

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first two-column layout and dark mode. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
