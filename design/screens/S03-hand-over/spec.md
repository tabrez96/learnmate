---
id: S03
name: Hand over
purpose: Confirm the session, note the session PIN and hand the device over
size: 1280x800
---

## Content and actions
- Summary: the subject as the first line's title, with the picked material under it ("Change", back to S02), lesson then test (or "Test only, 10 questions" in test-only mode), the Telegram alert rule, and that answers come from the books unless the student chooses to check outside them.
- Item 3 tells the parent about the leave-the-app alert and the 5-minute inactivity lock (S11).
- Session PIN card (gradient hero, right column): a new random 4-digit PIN is made when S03 opens and sent to Telegram at the same moment. Date and time chip, the 4 digits large, "It works for this session only."
- "Make a new PIN" asks for confirmation ("The current PIN will stop working"), then replaces the PIN, shows it and sends it to Telegram. Only before the session starts; during a session the Telegram message's "New PIN" button does the same without the device.
- "Hide PIN" masks the digits ("Show PIN" reveals them).
- "Start session and hand over" starts the session, sends "Omar started a session" to Telegram and opens S04.
- "Change" or Back to S02 discards this PIN; coming back makes a new one.

## States
- Main (screen.html): PIN shown. Dark (states/dark.html).
- Hidden (states/hidden.html): digits masked, "Show PIN".
- New PIN confirm (states/new-pin-confirm.html): dialog "Make a new PIN?".
- New PIN (states/new-pin.html): ok alert "New PIN made. The old one no longer works." and the new digits.
- Test only: item 2 reads "Test only: 10 questions, no lesson" and item 4 is dropped (no mentor in this session).
- Telegram disconnected: a warning alert replaces the Telegram line: "Telegram couldn't be reached, so the PIN wasn't sent. Note it now." The button stays available.

## Notes and open questions
- From "Start session and hand over" until the session ends on S08, the app shows only the student screens (S04-S07, S11 when locked) and the session pill.
- The PIN used to have its own screen (S10, now retired). It was merged here because it was a second confirmation step with the same button; one screen is quicker and the parent still sees the PIN before handing over.

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first layout, dark mode, Today's PIN reminder added. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- PIN card replaced by a note that the session PIN comes next; button now leads to S10. Test-only summary added. Requested in UX review.
- First summary line now names the subject, with the material under it. Requested in UX review (subject first).
- Merged S10 into S03: the session PIN, Make a new PIN (with confirmation) and Hide PIN now live here, and "Start session and hand over" goes straight to S04. Inactivity lock added to the summary. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
