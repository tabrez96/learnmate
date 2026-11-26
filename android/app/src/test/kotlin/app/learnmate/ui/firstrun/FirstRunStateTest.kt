package app.learnmate.ui.firstrun

import app.learnmate.domain.StepState
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class FirstRunStateTest {
    private val ready =
        FirstRunUiState(
            loading = false,
            childName = "Omar",
            grade = 7,
            familySaved = true,
            telegramConnected = true,
            password = SAMPLE_TYPED,
            passwordAgain = SAMPLE_TYPED,
        )

    @Test
    fun `can finish with everything set`() = assertTrue(ready.canFinish)

    @Test
    fun `can finish needs telegram`() = assertFalse(ready.copy(telegramConnected = false).canFinish)

    @Test
    fun `can finish needs the password`() = assertFalse(ready.copy(passwordAgain = SAMPLE_OTHER).canFinish)

    @Test
    fun `can finish with a server password and empty fields`() =
        assertTrue(ready.copy(fallbackSet = true, password = "", passwordAgain = "").canFinish)

    @Test
    fun `can finish waits for loading and busy`() {
        assertFalse(ready.copy(loading = true).canFinish)
        assertFalse(ready.copy(busy = true).canFinish)
    }

    @Test
    fun `can finish needs a child`() {
        assertFalse(ready.copy(childName = "  ").canFinish)
        assertFalse(ready.copy(grade = null).canFinish)
    }

    @Test
    fun `password length bounds`() {
        fun ok(n: Int) = FirstRunUiState(password = sampleOfLength(n), passwordAgain = sampleOfLength(n)).passwordReady
        assertFalse(ok(7))
        assertTrue(ok(8))
        assertTrue(ok(128))
        assertFalse(ok(129))
    }

    @Test
    fun `lengths count code points like the server`() {
        fun ok(n: Int): Boolean {
            val typed = "😀".repeat(n)
            return FirstRunUiState(password = typed, passwordAgain = typed).passwordReady
        }
        assertFalse(ok(4))
        assertTrue(ok(8))
    }

    @Test
    fun `name is limited to 100 characters after trimming`() {
        fun valid(name: String) = FirstRunUiState(childName = name, grade = 7).childValid
        assertTrue(valid("a".repeat(100)))
        assertTrue(valid(" " + "a".repeat(100) + " "))
        assertFalse(valid("a".repeat(101)))
        assertNull(nameError("a".repeat(100)))
        assertEquals("Use at most 100 characters", nameError("a".repeat(101)))
    }

    @Test
    fun `password needs an identical second entry`() =
        assertFalse(FirstRunUiState(password = SAMPLE_EIGHT, passwordAgain = SAMPLE_EIGHT_OTHER).passwordReady)

    @Test
    fun `password messages`() {
        assertNull(passwordError("", ""))
        assertEquals("Use at least 8 characters", passwordError(SAMPLE_SHORT, ""))
        assertNull(passwordError(SAMPLE_EIGHT, ""))
        assertEquals("Use at most 128 characters", passwordError(sampleOfLength(129), ""))
        assertNull(againError("abc", ""))
        assertNull(againError("abc", "abc"))
        assertEquals("The two passwords don't match", againError("abc", "abd"))
    }

    @Test
    fun `fresh steps`() {
        val s = FirstRunUiState(loading = false)
        assertEquals(StepState.Current, s.childStep)
        assertEquals(StepState.Upcoming, s.telegramStep)
        assertEquals(StepState.Upcoming, s.passwordStep)
    }

    @Test
    fun `step one saved`() {
        val s = FirstRunUiState(loading = false, childName = "Omar", grade = 7, familySaved = true)
        assertEquals(StepState.Done, s.childStep)
        assertEquals(StepState.Current, s.telegramStep)
        assertEquals(StepState.Upcoming, s.passwordStep)
    }

    @Test
    fun `telegram connected`() {
        val s = ready.copy(fallbackSet = false)
        assertEquals(StepState.Done, s.telegramStep)
        assertEquals(StepState.Current, s.passwordStep)
    }

    @Test
    fun `fallback set before telegram`() = assertEquals(StepState.Done, FirstRunUiState(fallbackSet = true).passwordStep)

    @Test
    fun `connected line`() {
        assertEquals("Connected: @omars_parent. Grades, alerts and session PINs arrive here.", connectedLine("omars_parent"))
        assertEquals("Connected. Grades, alerts and session PINs arrive here.", connectedLine(null))
        assertEquals("Connected. Grades, alerts and session PINs arrive here.", connectedLine(" "))
    }
}
