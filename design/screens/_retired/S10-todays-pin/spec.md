---
id: S10
name: Session PIN
purpose: Show the parent the PIN for the session they are about to start, just before hand-over
size: 1280x800
---

## Content and actions
- Shown once per session: S03 "Next: get the session PIN" -> S10 -> S04. It never appears at any other time, and never during a session.
- Learnmate makes a new random 4-digit PIN when S10 opens. The same PIN is sent to Telegram at the same moment.
- Chip with date and time, "Here's the PIN for this session", the 4 digits large.
- "It works for this session only. The next session gets a new one."
- "Start session and hand over" starts the session, sends "Omar started a session" to Telegram and opens S04.
- "Make a new PIN" replaces the PIN at once (new-pin state); the old one stops working and the new one goes to Telegram.
- "Hide PIN" masks the digits ("Show PIN" reveals them again).
- Telegram line: the PIN message in Telegram has a "New PIN" button, so the parent can regenerate it during the session without the device (the student never sees the new PIN).
- Side card: how the PIN works (new every session, regenerate any time, "Forgot the PIN?" resends the same one, fallback password after 3 wrong PINs).

## States
- Main (screen.html): PIN shown. Dark (states/dark.html).
- Hidden (states/hidden.html): digits masked, "Show PIN".
- New PIN (states/new-pin.html): after "Make a new PIN": an ok alert "New PIN made. The old one no longer works." and the new digits.
- Telegram not connected: cannot happen; setup requires Telegram (S01 first run). If Telegram is unreachable, a warning says the PIN couldn't be sent and the parent should note it now.

## Notes and open questions
- The PIN is shown on the shared device only here, before the student has it. The screen reminds the parent to keep it away from the student.
- "Make a new PIN" in Telegram during a session: rate-limited to once a minute; the end screen (S08) accepts only the newest PIN.

## Change log
- New screen: daily PIN shown on first open. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- Reworked as the Session PIN: a new PIN for every session, shown between S03 and S04 (no longer on first open each day); "Make a new PIN" here and "New PIN" in Telegram; new-pin state added. Requested in UX review.
