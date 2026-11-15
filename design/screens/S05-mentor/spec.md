---
id: S05
name: Mentor
purpose: Learn today's topic step by step and ask questions
size: 1280x800
---

## Content and actions
- Left panel: back to S04 (the lesson keeps its place), lesson title, "Step 3 of 6", progress bar, the list of steps, and the material being taught from.
- Chat: the mentor teaches one small idea, then asks a quick check. Teaching messages name their source ("From: Science notes, p.32").
- When the material doesn't cover a question, the mentor says so plainly and offers a "Check outside the books" button under its message.
- Visual block: a mentor reply can carry one visual under its text when a picture explains better than words (see "Visual answers" below).
- Composer row: quick replies "Next step" and "Explain again", then the text box and a split Send button.
  - "Send" (main part, default, Enter key): the answer comes only from the books.
  - The arrow part opens a menu: "Send" (books only, checked) and "Send and check outside the books". The menu choice applies to that one message; the next message goes back to books only.
- Answers checked outside the books sit in an amber bubble with the chip "Checked outside your books" and a "Source:" line naming the site.
- Visual answers: the visual sits inside the mentor bubble, under the text and above the source line, in an inset panel (Paper background in a mentor bubble, Card background in an amber outside bubble). Kinds:
  - Chart: a simple bar, line or pie chart for numbers and comparisons (at most 6 bars or slices, values printed on the chart, Blue, then violet #7B4FE0, then rose #B94A9E; never gold).
  - Step diagram: numbered boxes joined by arrows for a process (up to 5 steps in a row).
  - Table: a small table for facts side by side (up to 4 rows and 3 columns).
  - Notes image: a crop of the student's own uploaded page when the picture is the answer. Tapping it opens the whole page.
- Every visual has a one-line caption and a text alternative: charts carry a data table for screen readers, step diagrams are an ordered list, tables are real tables, notes images have a description of what the drawing shows.
- The source line stays under every visual ("From: Science notes, p.31"). A visual in an answer checked outside the books keeps the "Checked outside your books" chip and its "Source:" line. Notes images only ever come from the student's own material.
- After the last step, the mentor says "Ready for your test?" and a button goes to S06.

## States
- Main (screen.html): step 3, a teaching reply with a bar chart and an answer with an image cropped from the notes. Dark (states/dark.html).
- Visual answer (states/visual-answer.html, dark twin states/visual-answer-dark.html): step 4, a step-diagram reply from the notes and an outside-the-books answer with a small table, chip and source.
- Send menu (states/send-menu.html): the menu open above Send, with an earlier outside answer in the chat.
- Outside checking switched off in S09: the arrow part and the "Check outside the books" button are hidden; the footer reads "Answers come only from your books."
- Loading: a typing bubble (three dots); Send is disabled. A visual that is still being drawn shows a grey panel of its final size under the text, so the chat doesn't jump.
- Visual can't be shown (e.g. the notes page is missing): the text answer stays, and the panel reads "I couldn't show the picture, but the answer above still stands."
- Error: mentor bubble "I lost my connection. Your progress is saved." with "Try again".

## Notes and open questions
- The chat is aria-live="polite". The arrow part is a button with aria-haspopup="menu"; options are menuitemradio, arrow keys move, Escape closes.
- Each visual is a figure with a figcaption; the chart graphic itself is hidden from screen readers and its data table is read instead.
- The mentor picks a visual only where it helps; most replies stay text. Charts use values from the material; the mentor doesn't invent numbers.
- Quick replies moved into the composer row to give the chat room for visuals.

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first layout with a step panel, dark mode, and the split Send button with "Send and check outside the books". Requested in UX review.
- Visual block in mentor replies (chart, step diagram, table, notes image) with caption, text alternative and source; new visual-answer state with a dark twin; quick replies moved into the composer row. Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
