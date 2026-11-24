package app.learnmate.session.mentor

import app.learnmate.data.api.LessonCheckDto
import app.learnmate.data.api.LessonDto
import app.learnmate.data.api.LessonStepDto
import app.learnmate.data.api.PassageSourceDto
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class MentorStateTest {
    private val source = PassageSourceDto(1, "Science notes", "Chapter 4", 32)

    @Test
    fun `sourceLine uses page when present`() {
        assertEquals("From: Science notes, p.32", sourceLine(listOf(source)))
    }

    @Test
    fun `sourceLine falls back to chapter`() {
        assertEquals("From: Science notes, Chapter 4", sourceLine(listOf(source.copy(page = null))))
        assertNull(sourceLine(emptyList()))
    }

    @Test
    fun `outsideSourceLine strips www`() {
        assertEquals("Source: britannica.com", outsideSourceLine("https://www.britannica.com/x"))
        assertEquals("Source: khanacademy.org", outsideSourceLine("https://khanacademy.org/x"))
        assertEquals("Source: not a url", outsideSourceLine("not a url"))
        assertNull(outsideSourceLine(null))
        assertNull(outsideSourceLine(" "))
    }

    @Test
    fun `teachingFromLine uses the first step's first source`() {
        val step = LessonStepDto(0, "Light", "Body", LessonCheckDto("Q?", listOf("A")), listOf(source))
        assertEquals("Teaching from: Science notes, Chapter 4", teachingFromLine(LessonDto(7, "T", listOf(step))))
        assertNull(teachingFromLine(LessonDto(7, "T", emptyList())))
        assertNull(teachingFromLine(LessonDto(7, "T", listOf(step.copy(sources = emptyList())))))
    }

    @Test
    fun `checkResultText covers the three forms`() {
        assertEquals("Yes! +5 Because.", checkResultText(true, 5, "Because."))
        assertEquals("Yes! Because.", checkResultText(true, null, "Because."))
        assertEquals("Yes! Because.", checkResultText(true, 0, "Because."))
        assertEquals("Not quite, and that's okay. Because.", checkResultText(false, 5, "Because."))
    }

    @Test
    fun `canGoNext needs an answered check and a next step`() {
        fun check(answered: Int?) = ChatItem.Check("k", 0, "Q?", listOf("A", "B"), answered)
        val titles = listOf("One", "Two")
        assertFalse(MentorUiState(stepTitles = titles, items = listOf(check(null))).canGoNext)
        assertTrue(MentorUiState(stepTitles = titles, items = listOf(check(1))).canGoNext)
        assertFalse(MentorUiState(stepTitles = titles, items = listOf(check(1)), typing = true).canGoNext)
        assertFalse(MentorUiState(stepTitles = titles, stepIndex = 1, items = listOf(check(1))).canGoNext)
    }

    @Test
    fun `step label and progress follow the step`() {
        val state = MentorUiState(stepTitles = listOf("a", "b", "c", "d"), stepIndex = 1)
        assertEquals("Step 2 of 4", state.stepLabel)
        assertEquals(0.5f, state.progress)
        assertEquals(0f, MentorUiState().progress)
    }

    @Test
    fun `elapsedMinutes covers null, past, future and garbage`() {
        val now = 1_800_000_000_000L
        assertEquals(0, elapsedMinutes(null, now))
        assertEquals(0, elapsedMinutes("garbage", now))
        assertEquals(
            5,
            elapsedMinutes(
                java.time.Instant
                    .ofEpochMilli(now - 5 * 60_000)
                    .toString(),
                now,
            ),
        )
        assertEquals(
            0,
            elapsedMinutes(
                java.time.Instant
                    .ofEpochMilli(now + 60_000)
                    .toString(),
                now,
            ),
        )
    }
}
