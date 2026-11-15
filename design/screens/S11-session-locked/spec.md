---
id: S11
name: Session locked
purpose: Lock the session after 5 minutes with no activity, until a parent unlocks it with the session PIN
size: 1280x800
---

## Content and actions
- Applies to every student screen (S04-S07). Activity is any touch, key press or scroll. Time while the mentor is writing a reply does not count as inactivity.
- After 4 minutes with no activity, a warning dialog opens over the current screen (states/warning.html): "Still there, Omar?", a 60-second countdown ring, "I'm here, keep going" (primary). Any tap closes it and restarts the timer. No Telegram message at this point.
- At 5 minutes the session locks (screen.html):
  - Left: lock icon, "Session locked", when and why, the paused step ("Lesson with your mentor, step 4 of 6"), and the Telegram line.
  - Right: "Parent: enter the session PIN to continue", four PIN dots, the same keypad as S08 (88x72 px keys, Delete). The correct PIN returns to the exact screen and step that was open, and Telegram gets "Omar's session was unlocked (19:20)."
  - "Forgot the PIN? Send it to Telegram" resends the same session PIN (once a minute), as on S08.
  - "End the session instead" opens S08 with its normal rules (PIN, fallback password after 3 wrong PINs).
- On lock, Telegram gets "Omar's session locked after 5 minutes with no activity (19:12)." The session pill turns amber: "Locked, 31 min".
- Wrong PINs here count toward the same session limit as S08: 5 wrong tries lock the pad for 15 minutes, and after 3 wrong tries "PIN not working? Use the fallback password" appears, which can only end the session (S08 fallback state).

## States
- Locked (screen.html). Dark (states/dark.html).
- Warning (states/warning.html, over S04): countdown at 0:45. Dark (states/warning-dark.html).
- Wrong PIN and pad lockout: as S08 states/wrong-pin.html and states/locked.html, with "continue" in place of "end".
- During a test (S06): the timer still runs; after unlocking, the test resumes at the same question with the chosen answer kept.

## Notes and open questions
- The 4-minute warning and 5-minute lock are first guesses; tune with use. They are fixed in the MVP (no setting).
- Locked minutes are left out of study time; the session summary (S08 ended state) and Telegram summary count the locks ("Locked once for no activity, 8 min").
- Leaving the app (flow 7) is separate: it alerts but doesn't lock. If the app is in the background for 5 minutes, it opens locked.
- Focus: the warning's button gets focus and the dialog is an alertdialog; the countdown is announced once, not every second. On the locked screen, focus starts on the keypad and digits can be typed.
- Reduced motion: the ring doesn't animate; the number still counts down.

## Change log
- New screen: inactivity warning at 4 minutes and parent-PIN lock at 5 minutes, with Telegram messages on lock and unlock. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
