---
id: S08
name: End session (parent PIN)
purpose: A parent ends the session with the session PIN, or force-ends it with the fallback password as a last resort
size: 1280x800
---

## Content and actions
- Left: "Parent: enter the session PIN to end the session", a one-line session recap, messages, and "Keep studying" (back to S04).
- Right: four PIN dots, keypad with 88x72 px keys and Delete. The PIN is checked when the fourth digit is entered. Only the newest session PIN works (see S03 "Make a new PIN" and "New PIN" in Telegram).
- "Forgot the PIN? Send it to Telegram" sends the session PIN again (the same PIN, not a new one).
- "PIN not working? Use the fallback password": hidden until 3 wrong PINs in this session, then stays visible (also while the pad is locked). Opens the fallback state.
- Correct PIN or fallback password ends the session and shows the ended state.

## States
- Main (screen.html): two digits entered. Dark (states/dark.html).
- Wrong PIN (states/wrong-pin.html): the third wrong try: "2 tries left before the pad locks for 15 minutes", dots clear, and the fallback link appears.
- Locked (states/locked.html): after 5 wrong tries, a countdown; the session keeps running; the parent is told on Telegram. The fallback link stays available.
- PIN sent (states/pin-sent.html): "The session PIN was sent to your Telegram again. It's the same PIN as when the session started."
- Fallback (states/fallback.html): "Force end the session", a password field with Show, "Force end session", "Back to the PIN pad". A warning says Telegram will be told. 3 wrong passwords lock the fallback for 1 hour (parent told on Telegram).
- Ended (states/ended.html): session summary (time studied, test grade, points, times the student left Learnmate, inactivity locks and their minutes, a timeline), sent to Telegram; "Back to home" goes to S01. When force-ended, the timeline and the Telegram summary add "Force-ended with the fallback password".

## Notes and open questions
- If the student leaves the app, the parent gets "Omar left Learnmate during the session (18:51)." and "Omar is back (18:53)." The summary counts these.
- Keyboard: digits can be typed on a physical keyboard; focus starts on the pad. In the fallback state focus starts on the password field.
- Resending is limited to once a minute so repeated taps don't flood Telegram.
- The fallback password is never sent to Telegram, so it still works when Telegram or the network is down. It is set during setup (S01) and changed in S09.

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first layout, dark mode; PIN is now today's daily PIN and "Forgot" resends the same PIN instead of a one-time PIN. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- PIN is now per session; fallback password link after 3 wrong PINs and new fallback state to force-end the session. Requested in UX review.
- PIN references point to S03 (S10 retired); the session summary counts inactivity locks (S11). Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
