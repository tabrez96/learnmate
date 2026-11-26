package app.learnmate.session

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class InactivityTimerTest {
    private var nowMs = 1_000L
    private val timer = InactivityTimer(warnAfterMs = 240_000, lockAfterMs = 300_000, startMs = nowMs)

    private fun at(elapsed: Long): InactivityPhase = timer.phase(1_000 + elapsed)

    @Test
    fun `active before warn`() = assertEquals(InactivityPhase.Active, at(239_999))

    @Test
    fun `warning at warn`() = assertEquals(InactivityPhase.Warning, at(240_000))

    @Test
    fun `locked at lock and latched`() {
        assertEquals(InactivityPhase.Locked, at(300_000))
        timer.onActivity(1_000 + 300_001)
        assertEquals(InactivityPhase.Locked, at(300_002))
    }

    @Test
    fun `activity during warning resets`() {
        assertEquals(InactivityPhase.Warning, at(250_000))
        timer.onActivity(1_000 + 250_000)
        assertEquals(InactivityPhase.Active, at(251_000))
        assertEquals(InactivityPhase.Warning, at(490_000))
    }

    @Test
    fun `activity after lock is ignored`() {
        at(300_000)
        timer.onActivity(1_000 + 310_000)
        assertEquals(InactivityPhase.Locked, at(311_000))
    }

    @Test
    fun `activity after the lock deadline but before a tick still locks`() {
        assertEquals(InactivityPhase.Warning, at(299_999))
        timer.onActivity(1_000 + 300_001)
        assertEquals(InactivityPhase.Locked, at(300_002))
    }

    @Test
    fun `paused time does not count`() {
        timer.pause(1_000 + 100_000)
        timer.pause(1_000 + 150_000) // no-op while paused
        assertEquals(InactivityPhase.Active, at(900_000))
        timer.resume(1_000 + 400_000) // paused for 300 s
        assertEquals(InactivityPhase.Active, at(539_999))
        assertEquals(InactivityPhase.Warning, at(540_000))
        timer.resume(1_000 + 560_000) // not paused: no-op
        assertEquals(InactivityPhase.Warning, at(560_000))
    }

    @Test
    fun `activity while paused counts from the pause`() {
        timer.pause(1_000 + 100_000)
        timer.onActivity(1_000 + 200_000)
        timer.resume(1_000 + 400_000)
        assertEquals(300, timer.secondsToLock(1_000 + 400_000))
    }

    @Test
    fun `secondsToLock counts down to 0`() {
        assertEquals(300, at(0).let { timer.secondsToLock(1_000) })
        assertEquals(60, timer.secondsToLock(1_000 + 240_000))
        assertEquals(1, timer.secondsToLock(1_000 + 299_001))
        assertEquals(0, timer.secondsToLock(1_000 + 900_000))
    }

    @Test
    fun `unlock restarts the timer`() {
        at(300_000)
        timer.pause(1_000 + 305_000)
        timer.unlock(1_000 + 310_000)
        assertEquals(InactivityPhase.Active, at(311_000))
        assertEquals(InactivityPhase.Warning, at(310_000 + 240_000))
    }

    @Test
    fun `warn must be below lock`() {
        assertThrows(IllegalArgumentException::class.java) { InactivityTimer(300, 300, 0) }
        assertThrows(IllegalArgumentException::class.java) { InactivityTimer(0, 300, 0) }
    }
}
