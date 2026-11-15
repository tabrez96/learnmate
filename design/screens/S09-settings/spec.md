---
id: S09
name: Settings
purpose: Manage appearance, Telegram, the PIN and fallback password, subjects and their material, exam dates and the mentor
size: 1280x1200
---

## Content and actions
- Left: section list (Appearance, Telegram, PIN and password, Subjects and material, Exam dates, Mentor, Delete data); tapping scrolls to the section.
- Appearance: Light / Dark / Match device (default Match device). The sun and moon switch in the top bar flips between light and dark directly.
- Telegram: connected account, "Send a test message"; when not connected, "Connect Telegram" opens the bot link.
- PIN and fallback password: explains the session PIN (new for every session, shown on S03 before hand-over, "New PIN" in Telegram). Fallback password status (Set, with date) and "Change fallback password", a dialog asking for the current password, then the new one twice. If the current one is forgotten, the change can be confirmed with a code sent to Telegram.
- Subjects and material: a list of subjects, each a disclosure row (icon, name, material count and average grade). Opening a subject shows its materials, newest first, each with Delete (asks for confirmation), and the subject's actions: "+ Add material" (add-material dialog for that subject), "Rename" and "Delete subject" (confirmation; deletes its material, keeps past grades). "+ Add subject" opens a small dialog with a name field. One subject is open at a time.
- Exam dates: subject and date list, add and edit. Surprise tests appear in the week before each date.
- Mentor: "Allow checking outside the books" switch, on by default. Off hides the "Send and check outside the books" option on S05.
- "Delete all of Omar's material and results": confirmation dialog that asks for the fallback password.

## States
- Main (screen.html): Science open with three materials, the other subjects closed. Dark (states/dark.html).
- Add material (states/add-material.html, dark twin states/add-material-dark.html): dialog opened from Science, with the Subject field pre-filled (it can be changed, or set to "+ New subject"), upload area, a file being read and a Classroom link; "Add to Science" saves it under that subject for S02.
- Empty subject: the open subject says "No material yet." above "+ Add material".
- No subjects: "Add a subject, like Science or Maths, then add its notes." with "+ Add subject".
- Empty exam dates: "No exams added. Add one to get surprise tests before it."

## Notes and open questions
- Settings is only reachable from the parent side, never during a session.
- The page scrolls; the screenshot shows its full height.

## Change log
- Created for the first UX of the MVP brief.
- Tablet-first layout with section list, dark mode, Appearance section, Add material, daily PIN section (Change PIN removed), outside-books switch now controls the per-message option. Requested in UX review.
- Sample student renamed to Omar in all states. Requested in UX review.
- Today's PIN section replaced by PIN and fallback password (session PIN explained, change fallback password); delete-data now confirms with the fallback password. Requested in UX review.
- Material section replaced by Subjects and material: subjects hold their materials, with add, rename and delete per subject; the add-material dialog takes a subject; dark twin added for it. Requested in UX review.
- Session PIN is now shown on S03 (S10 retired). Requested in UX review.
- Modern visual refresh from the shared design system (floating frosted top bar, page glow, borderless cards with layered shadows, rounder corners, glow on gradient actions), in light and dark. Layout, copy and flow unchanged. Requested in UX review.
- Settings navigation: the active item's marker is now a short rounded 4 px Blue bar, inset and vertically centred, instead of a full-height inset edge that bent around the item's rounded corners. Requested in UX review.
