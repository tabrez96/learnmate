package app.learnmate

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class SampleTest {
    @Test
    fun junitPlatformRuns() {
        assertEquals(listOf(1, 2, 3), listOf(3, 1, 2).sorted())
    }
}
