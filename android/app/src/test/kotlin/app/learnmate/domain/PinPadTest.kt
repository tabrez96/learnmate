package app.learnmate.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds

class PinPadTest {
    private val now = Instant.parse("2026-01-01T10:00:00Z")

    private fun PinPadState.wrongTimes(n: Int) = (1..n).fold(this) { s, _ -> s.wrong(now) }

    @Test
    fun `typed appends up to length and ignores extra digits`() {
        var s = PinPadState()
        "48219".forEach { s = s.typed(it.digitToInt(), now) }
        assertEquals("4821", s.digits)
        assertTrue(s.isComplete)
        assertEquals(s, s.typed(12, now))
    }

    @Test
    fun `delete removes last digit`() {
        val s = PinPadState().typed(1, now).typed(2, now).deleted()
        assertEquals("1", s.digits)
        assertEquals("", PinPadState().deleted().digits)
    }

    @Test
    fun `typing is ignored while locked`() {
        val locked = PinPadState().wrongTimes(5)
        assertEquals("", locked.typed(1, now).digits)
    }

    @Test
    fun `third local wrong shows fallback and 2 tries left`() {
        val s = PinPadState().typed(1, now).wrongTimes(3)
        assertTrue(s.fallbackAvailable)
        assertEquals("", s.digits)
        assertEquals(
            PinNotice.Wrong("That's not the session PIN. 2 tries left before the pad locks for 15 minutes."),
            s.notice(now),
        )
        assertFalse(PinPadState().wrongTimes(2).fallbackAvailable)
    }

    @Test
    fun `typing after a wrong try clears the red state`() {
        val s = PinPadState().wrongTimes(1).typed(5, now)
        assertFalse(s.showWrong)
        assertEquals(PinNotice.None, s.notice(now))
    }

    @Test
    fun `fourth wrong says 1 try left`() {
        val notice = PinPadState().wrongTimes(4).notice(now) as PinNotice.Wrong
        assertEquals("That's not the session PIN. 1 try left before the pad locks for 15 minutes.", notice.text)
    }

    @Test
    fun `fifth wrong locks for 15 minutes and resets tries`() {
        val s = PinPadState().wrongTimes(5)
        assertEquals(now.plusSeconds(900), s.lockedUntil)
        assertEquals(5, s.triesLeft)
        assertTrue(s.isLocked(now))
        assertTrue(s.fallbackAvailable)
    }

    @Test
    fun `tenth wrong locks again`() {
        val later = now.plusSeconds(1000)
        val s = PinPadState().wrongTimes(5).wrongTimes(4).wrong(later)
        assertEquals(later.plusSeconds(900), s.lockedUntil)
        assertTrue(s.fallbackAvailable)
    }

    @Test
    fun `locked notice shows m ss countdown`() {
        val s = PinPadState().wrongTimes(5)
        val notice = s.notice(now.plusSeconds(8)) as PinNotice.Locked
        assertEquals("Too many wrong tries.", notice.title)
        assertEquals(
            "The pad is locked for 14:52. The session keeps running, and we told you on Telegram.",
            notice.text,
        )
    }

    @Test
    fun `lock ends when the clock passes lockedUntil`() {
        val s = PinPadState().wrongTimes(5)
        assertTrue(s.isLocked(now.plusSeconds(899)))
        assertFalse(s.isLocked(now.plusSeconds(900)))
        assertEquals("1", s.typed(1, now.plusSeconds(900)).digits)
    }

    @Test
    fun `serverWrong and serverLocked map the API errors`() {
        val wrong = PinPadState().typed(1, now).serverWrong(triesLeft = 2, fallbackAvailable = true)
        assertEquals(1, wrong.wrongCount)
        assertEquals(2, wrong.triesLeft)
        assertTrue(wrong.fallbackAvailable)
        assertTrue(wrong.showWrong)
        assertEquals("", wrong.digits)

        val locked = wrong.serverLocked(120, fallbackAvailable = false, now = now)
        assertEquals(now.plusSeconds(120), locked.lockedUntil)
        assertEquals(5, locked.triesLeft)
        assertTrue(locked.fallbackAvailable)
    }

    @Test
    fun `local wrong after a server lockout keeps the fresh tries`() {
        val s = (1..4).fold(PinPadState()) { p, _ -> p.serverWrong(1, true) }
        val unlocked = s.serverLocked(900, fallbackAvailable = true, now = now)
        val after = unlocked.wrong(now.plusSeconds(901))
        assertEquals(4, after.triesLeft)
        assertFalse(after.isLocked(now.plusSeconds(901)))
    }

    @Test
    fun `cleared drops the digits only`() {
        val s = PinPadState().typed(1, now).typed(2, now).cleared()
        assertEquals("", s.digits)
    }

    @Test
    fun `countdown rounds up and never goes negative`() {
        assertEquals("14:52", countdown(892.seconds))
        assertEquals("1:00", countdown(60.seconds))
        assertEquals("0:01", countdown(400.milliseconds))
        assertEquals("0:00", countdown((-5).seconds))
        assertEquals("0:09", countdown(9.seconds))
    }
}
