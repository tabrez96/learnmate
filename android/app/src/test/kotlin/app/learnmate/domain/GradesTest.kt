package app.learnmate.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class GradesTest {
    @Test
    fun `band boundaries`() {
        val expected =
            mapOf(
                100 to GradeBand.A,
                90 to GradeBand.A,
                89 to GradeBand.B,
                80 to GradeBand.B,
                79 to GradeBand.C,
                70 to GradeBand.C,
                69 to GradeBand.D,
                60 to GradeBand.D,
                59 to GradeBand.E,
                50 to GradeBand.E,
                49 to GradeBand.F,
                0 to GradeBand.F,
            )
        expected.forEach { (pct, band) -> assertEquals("pct $pct", band, gradeBand(pct)) }
    }

    @Test
    fun `out of range throws`() {
        assertThrows(IllegalArgumentException::class.java) { gradeBand(-1) }
        assertThrows(IllegalArgumentException::class.java) { gradeBand(101) }
    }

    @Test
    fun `missed wins over a score`() {
        assertEquals(Grade.Missed, gradeOf(80, "B", missed = true))
        assertEquals("Missed", Grade.Missed.LABEL)
    }

    @Test
    fun `server band is used when present`() {
        assertEquals(Grade.Scored(85, GradeBand.A), gradeOf(85, "A", missed = false))
        assertEquals(Grade.Scored(85, GradeBand.B), gradeOf(85, "?", missed = false))
        assertEquals(Grade.Scored(40, GradeBand.F), gradeOf(40, null, missed = false))
    }

    @Test
    fun `no score and not missed is null`() {
        assertNull(gradeOf(null, null, missed = false))
    }

    @Test
    fun `label is 80 percent B`() {
        assertEquals("80% B", (gradeOf(80, "B", false) as Grade.Scored).label)
    }
}
