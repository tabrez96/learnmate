# Learnmate: UX spec

## Users and primary jobs
- **Parent** (sets up, buyer): choose today's subject, then its material (from the library or new) or a test on chosen chapters, note the session PIN, start a locked study session and hand over the tablet, end it with the PIN (or the fallback password as a last resort), see grades (in the app and on Telegram).
- **Student** (grade 5-10): follow today's plan, learn the topic with the mentor, finish with a test, earn points and keep the streak.

## Information architecture
An Android app, designed **tablet-first** (1280x800 landscape, two-column layouts). On phones the same screens stack into one column below 720 px wide. Every screen exists in light and dark mode (`states/dark.html`).

Parent side (no session running):
- S01 Parent home (first-run setup is a state of S01)
- S02 Today's material (subject first, then its material; add new, recap, or test only)
- S03 Hand over (session summary, the session PIN, Make a new PIN, Start session and hand over)
- S09 Settings (appearance, Telegram, PIN and fallback password, subjects and their material, exam dates, mentor)

Material always belongs to one subject. Subjects are the entry point: a session or test starts by picking one subject, then material or chapters from it.

Student side (session running; locked):
- S04 Session home (today's plan, points, streak, level)
- S05 Mentor
- S06 Test
- S07 Test result
- S11 Session locked (after 5 minutes with no activity; warning at 4 minutes)

Bridge:
- S08 End session (session PIN; fallback password after 3 wrong PINs), plus the session summary.

While a session runs, only S04-S08 and S11 are reachable. Every student screen shows the session pill (lock icon and minutes). The light/dark switch is in the top bar of every screen.

## Key flows
1. **First run**: S01 first-run state: child name and grade, connect Telegram, choose a fallback password -> S01.
2. **Session PIN**: every session gets a new random 4-digit PIN, made when S03 opens and sent to Telegram at the same time. It is shown on the device only on S03, before hand-over. "Make a new PIN" on S03 (with confirmation), or "New PIN" in the Telegram message during the session, replaces it; the old one stops working at once.
3. **Daily session**: S01 "Start today's session" (the Today card names no chapter: nothing is known until material is picked) -> S02 pick the subject, then pick its material and/or add notes or a Classroom link to it, optionally name chapters -> S03 confirm and note the session PIN, "Start session and hand over" (Telegram: session started) -> S04 warm-up -> S05 lesson -> S06 test -> S07 result (Telegram: grade) -> S08 session PIN -> summary (Telegram: summary) -> S01.
4. **Recap day**: S02 "Nothing new today: recap an earlier chapter" -> pick the subject -> pick one of its chapters -> S03 -> same as flow 3 with a recap lesson.
4a. **Test only**: S02 session type "Test only" -> pick the subject -> pick one or more of its chapters and 5 / 10 / 15 questions -> S03 -> S04 (warm-up, then the test; no lesson) -> S06 -> S07 (Telegram: grade) -> S08.
5. **Add material ahead of time**: S09 open a subject (or "+ Add subject") -> "+ Add material" -> upload or Classroom link -> it appears under that subject in S02.
6. **Checking outside the books**: S05 the student types a question -> the arrow next to Send -> "Send and check outside the books" -> the answer is marked "Checked outside your books" with its source. Plain Send always answers from the books only. When the mentor can't answer from the books, it offers the same option as a button.
7. **Student leaves the app**: Telegram alert on hide/close; "back" message on return; the count appears in the session summary. Closing mid-test resumes at the same question.
8. **Student wants to stop early**: S04 "I'm done: ask a parent to end" -> S08 notes the test will be recorded as missed -> session PIN.
9. **Forgotten PIN**: S08 "Forgot the PIN? Send it to Telegram" -> the same session PIN is sent again (at most once a minute). 5 wrong tries lock the pad for 15 minutes; the session keeps running and the parent is told.
9a. **Force end (last resort)**: after 3 wrong PINs in a session, S08 shows "PIN not working? Use the fallback password" -> fallback state -> the password force-ends the session (Telegram: force-ended with the fallback password) -> summary. 3 wrong passwords lock it for 1 hour. The fallback password is set in first run and changed in S09; it is never sent to Telegram, so it works offline.
7a. **Inactivity lock**: on S04-S07, 4 minutes with no touch or key -> S11 warning "Still there?" with a 60-second countdown (any tap continues) -> at 5 minutes the session locks (S11; Telegram: locked for no activity) -> a parent enters the session PIN -> back to the same screen and step (Telegram: unlocked). "End the session instead" goes to S08. Wrong PINs share S08's limits. Locked minutes don't count as study time and the summary lists the locks.
10. **Exam season**: S09 add exam date -> in the week before it, S04 may show a surprise test in place of the daily test.
11. **Appearance**: the sun/moon switch in the top bar flips light and dark; S09 Appearance also offers Match device (the default).

## Design system
**Mood**: a tidy notebook at sunrise. Warm paper in light mode, deep ink-blue at night, one gradient (indigo to violet to rose) for the brand, primary actions and hero cards, and warm gold kept for rewards. The surface style is soft and modern: a faint indigo and violet glow behind the page, borderless cards that float on layered shadows, a floating frosted top bar, rounder corners, and a soft coloured glow under gradient actions.

Colours:
| Token | Light | Dark | Use |
|---|---|---|---|
| Paper | #F7F5EF | #11152A | page background |
| Card | #FFFFFF | #1B2040 | cards, options, keys, top bar |
| Line | #E7E3D8 | #2E3560 | borders, dividers, empty bar |
| Ink | #1E2640 | #EEF0FA | text |
| Ink soft | #5B6478 | #A7AECB | secondary text |
| Blue | #3949C8 | #8E9BFF | links, focus ring, selected borders |
| Blue tint / text | #ECEEFB / #2C3AA8 | #272F66 / #C3C9FF | chips, selected options |
| Brand gradient | #3949C8 -> #6A4BD8 -> #9B4DCB (135deg) | same | primary buttons, hero cards, current step (white text at least 4.8:1) |
| Text gradient | #3949C8 -> #7B4FE0 -> #B94A9E | #9AA6FF -> #C3A2FF -> #FF9CC8 | "mate" in the wordmark, big score |
| Gold gradient | #F2A516 -> #F57C4B | same | points, level bar, rewards only (never text) |
| Green / tint / text | #1F9D6B / #E2F4EC / #13704B | #3CC48C / #16392E / #7FE0B4 | correct, done, session pill |
| Red / tint / text | #D64545 / #FBE5E5 / #A92F2F | #F06A6A / #45212A / #FFA8A8 | wrong, errors, delete |
| Amber tint / text | #FFF1D6 / #8A5A00 | #3B3016 / #F2C76B | warnings, "No session yet", outside-the-books answers |
| Telegram tint / text | #E8F4FB / #14567A | #15314A / #93CDF2 | Telegram confirmations |

Type (system font stack): H1 32/37 extra-bold, -0.8 px tracking (28 on phone); headings tighten slightly (-0.3 px); H2 20 bold; body 16; small 13-15; score 96 black. Sentence case everywhere.

Spacing: 4 px base; screen padding 24 x 32 on tablet (20 on phone); gap between blocks 16-24; card padding 20; radius 24 cards and dialogs, 20 stat tiles, answer options and keys, 16 buttons, rows and alerts, 14 inputs, 999 pills. Top bar 64 px, floating 12 px from the top and 16 px from the sides, radius 20, translucent card colour (72%) with a background blur.

Surfaces: page background is Paper with two large soft radial glows (Blue top-left, violet top-right; 10% in light, about 22-25% in dark). Cards, stat tiles and mentor bubbles have a hairline border (Ink at 6% in light, white at 7% in dark) and a layered shadow (light: 0 8 24 -6 Ink 10% plus 0 24 48 -24 Blue 18%; dark: a 1 px inner top highlight and a deep black drop shadow). Gradient buttons, the current step dot and student bubbles carry a violet glow (0 8 24 -8 #6A4BD8 55%). Hero cards add two soft light circles (white top-right, rose bottom) behind their content. Selected rows and options show a 4 px Blue halo (14%) around the 2 px Blue border. Secondary buttons and quick replies are Blue tint filled with a soft blue outline. The session pill starts with a small green live dot. Dialog scrims blur what is behind them. Progress bars are 8 px.

Layouts: parent screens use two columns (main 1.55 : side 1, or even halves); the mentor uses a 300 px step panel plus chat; the test is a centred 900 px column with a 2x2 answer grid.

Components: primary (gradient) / secondary / ghost buttons (min 52 px high, ghost 44); split button (Send plus menu arrow); card and gradient hero card; stat tile; step row with numbered dot (done = green check, now = gradient); progress bar; chip (blue, ok, warn, bad, grey "Missed"); chat bubbles (mentor card-coloured with source line, student gradient, outside-the-books amber with chip and source); visual block inside a mentor bubble (an inset panel under the text, above the source line: bar, line or pie chart; step diagram; small table; image cropped from the student's notes; each with a one-line caption and a text alternative, and the outside-the-books chip and source kept when it applies; chart colours Blue, violet #7B4FE0, rose #B94A9E, never gold); subject tile (radio, icon, name, material count and latest grade, "+ New subject" tile); subject disclosure row with nested material list; library row with checkbox; answer option (default, selected, right, wrong); PIN digit boxes, PIN dots and 3x4 keypad (88x72 px keys); password field with Show; alert (error, info, warning, ok); Telegram line; toggle switch; segmented control; side navigation (active item: Blue tint fill plus a short 4x20 px rounded Blue bar, inset 8 px from the left edge and vertically centred, so it never bends around the item's corners); light/dark switch (sun/moon); dialog with scrim; session pill.

Grades: percentage plus band. A 90-100, B 80-89, C 70-79, D 60-69, E 50-59, F below 50. A missed test is a grey "Missed" chip, never 0%.

Tone of voice: to the student, short, warm and upbeat ("Yes! +10", "Surprise test!"), never shaming a wrong answer ("Not quite, and that's okay."); to the parent, calm and factual ("Grade sent to Telegram"). The mentor admits when the books don't cover something and offers to check outside them.

Emoji are used as small decorative icons in the mockups (streak flame, star, badge); the build may swap them for an icon set of the same meaning. Decorative icons are hidden from screen readers.

### Logo
The mark is an open book whose left page ends in a speech-bubble tail, with a golden tick (#F2A516) on the right page, in white on a rounded square filled with a gradient from Blue #3949C8 to lighter indigo #5C6BE0 (top-left to bottom-right). It says: a mentor that talks you through your own book, and a check that the work was done. The gold tick is the same gold as the rewards. The gradient square carries the mark on light and dark backgrounds and is the Android app icon and favicon. `logo.svg` sets the mark beside "Learnmate" in Ink with "mate" in the same #3949C8 -> #5C6BE0 gradient; on dark backgrounds use the wordmark in white (with "mate" in the dark text gradient) or the mark alone. Keep at least a quarter of the mark's width clear around it; don't recolour the tick or pages, flatten the gradient, or rotate the mark.

## Accessibility
- Text contrast at least 4.5:1 in both modes (Ink soft is the lightest text). White on the brand gradient is at least 4.8:1. Gold is never used for text.
- Touch targets at least 44 px; answer options 84 px, keys 88x72 px.
- Visible focus ring: 3 px Blue outline with 2 px offset on every control (lighter blue in dark mode).
- Focus order follows reading order (left column, then right); on S08 focus starts on the keypad and digits can be typed; in the fallback state it starts on the password field.
- Mentor visuals are figures with captions; charts are backed by a data table for screen readers, step diagrams are ordered lists, tables are real tables, notes images carry a description.
- The inactivity warning (S11) is an alertdialog with focus on "I'm here, keep going"; the countdown is announced once, not every second, and doesn't animate under reduced motion.
- Mentor chat is an aria-live polite region; errors use role="alert"; confirmations role="status".
- The Send menu is a menu button (aria-haspopup, aria-expanded) with menuitemradio options; Escape closes it.
- Right/wrong is shown by text ("Correct!", "Your answer") and border colour, never colour alone. Outside-the-books answers carry a text chip, not just a colour.
- Toggles and the light/dark switch are role="switch" with aria-checked; library rows are checkboxes; the subject row is a radiogroup; subject rows in S09 are disclosure buttons with aria-expanded.
- Respect reduced motion: no confetti or shaking when it's set.

## Open questions
- Detecting "left the app" is best effort even on Android (lifecycle events plus a heartbeat); kiosk-style screen pinning could make it stronger later. The alert copy says "left Learnmate", not "closed".
- S03 shows the session PIN on the shared tablet just before hand-over; a family could choose Telegram only later.
- The fallback password lock (3 tries, 1 hour) is a first guess, like the PIN lockout. So are the inactivity timings (warning at 4 minutes, lock at 5).
- "Allow checking outside the books" is on by default, because each outside answer is a deliberate per-message choice and is clearly marked; plain Send stays books-only.
- Points values and level thresholds are first guesses (see S04 spec); tune after a few weeks of use.
