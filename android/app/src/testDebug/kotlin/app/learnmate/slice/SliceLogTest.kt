package app.learnmate.slice

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SliceLogTest {
    private val log = SliceLog()

    @Test
    fun `markdown lists every question with sources and time`() {
        log.answers += AnswerEntry("What is a cell?", 2300, listOf(SourceRef("file.pdf", 4), SourceRef("file.pdf", 5)), false)
        log.answers += AnswerEntry("Who won in 1990?", 800, emptyList(), false)
        val md = log.toMarkdown()
        assertTrue(md.contains("| 1 | What is a cell? | file.pdf p.4, file.pdf p.5 | 2.3 |"))
        assertTrue(md.contains("| 2 | Who won in 1990? | refused | 0.8 |"))
    }

    @Test
    fun `outside and failed answers are labelled`() {
        log.answers += AnswerEntry("a", 1000, emptyList(), true)
        log.answers += AnswerEntry("b", 1000, emptyList(), false, failed = "IOException")
        val md = log.toMarkdown()
        assertTrue(md.contains("| 1 | a | outside | 1.0 |"))
        assertTrue(md.contains("| 2 | b | error: IOException | 1.0 |"))
    }

    @Test
    fun `refused only when no sources, not outside and no error`() {
        val source = listOf(SourceRef("x.pdf", 1))
        assertTrue(AnswerEntry("q", 1, emptyList(), false).refused)
        assertFalse(AnswerEntry("q", 1, source, false).refused)
        assertFalse(AnswerEntry("q", 1, emptyList(), true).refused)
        assertFalse(AnswerEntry("q", 1, emptyList(), false, failed = "IOException").refused)
    }

    @Test
    fun `cost is after minus before`() {
        log.spentBefore = 1.25
        assertNull(log.cost)
        assertTrue(log.toMarkdown().contains("- This run: Not recorded"))
        log.spentAfter = 1.4
        val md = log.toMarkdown()
        assertTrue(md.contains("- Spent before: $1.2500"))
        assertTrue(md.contains("- Spent after: $1.4000"))
        assertTrue(md.contains("- This run: $0.1500"))
    }

    @Test
    fun `pipes in questions and titles are escaped`() {
        log.answers += AnswerEntry("a|b", 1, emptyList(), false)
        log.lesson += LessonEntry("c|d", emptyList())
        val md = log.toMarkdown()
        assertTrue(md.contains("a\\|b"))
        assertTrue(md.contains("c\\|d"))
    }

    @Test
    fun `pipes in source names are escaped`() {
        log.lesson += LessonEntry("t", listOf(SourceRef("Cells | revision", 2)))
        log.answers += AnswerEntry("q", 1, listOf(SourceRef("Cells | revision", 2)), false)
        assertEquals(2, Regex("Cells \\\\\\| revision p\\.2").findAll(log.toMarkdown()).count())
    }

    @Test
    fun `missing page shows a question mark`() {
        assertEquals("x.pdf p.?", SourceRef("x.pdf", null).toString())
        assertEquals("x.pdf p.3", SourceRef("x.pdf", 3).toString())
    }

    @Test
    fun `empty log says not recorded and material renders its fields`() {
        assertEquals(3, Regex("Not recorded").findAll(SliceLog().toMarkdown().substringBefore("## AI cost")).count())
        log.material = "Ch1"
        log.pagesRead = 4
        log.chapters = listOf("A", "B")
        log.readingMillis = 12_340
        log.lessonMillis = 3_000
        log.lesson += LessonEntry("Step", listOf(SourceRef("Ch1", 2)))
        val md = log.toMarkdown()
        assertTrue(md.contains("- File: Ch1"))
        assertTrue(md.contains("- Pages read: 4 of ?"))
        assertTrue(md.contains("- Chapters found: A; B"))
        assertTrue(md.contains("- Time to ready: 12.3 s"))
        assertTrue(md.contains("Generated in 3.0 s."))
        assertTrue(md.contains("| 1 | Step | Ch1 p.2 |"))
    }
}
