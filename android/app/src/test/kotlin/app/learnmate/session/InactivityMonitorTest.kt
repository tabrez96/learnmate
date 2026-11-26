package app.learnmate.session

import app.learnmate.data.presence.PresenceEvent
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.currentTime
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class InactivityMonitorTest {
    private val recorded = mutableListOf<PresenceEvent>()
    private val activity = MutableSharedFlow<Unit>()

    private fun TestScope.monitor() =
        InactivityMonitor(InactivityTimer(240_000, 300_000, 0), { testScheduler.currentTime }, {
            recorded +=
                it
        })

    @Test
    fun `records warned then locked once each`() =
        runTest {
            val m = monitor()
            val job = m.start(this, activity)
            advanceTimeBy(239_000)
            assertEquals(emptyList<PresenceEvent>(), recorded)
            advanceTimeBy(1_001)
            assertEquals(listOf(PresenceEvent.WARNED), recorded)
            assertEquals(InactivityPhase.Warning, m.phase.value)
            advanceTimeBy(60_000)
            assertEquals(listOf(PresenceEvent.WARNED, PresenceEvent.LOCKED), recorded)
            advanceTimeBy(600_000)
            assertEquals(2, recorded.size)
            assertEquals(InactivityPhase.Locked, m.phase.value)
            job.cancel()
        }

    @Test
    fun `activity emission resets the timer`() =
        runTest {
            val m = monitor()
            val job = m.start(this, activity)
            advanceTimeBy(250_000)
            assertEquals(InactivityPhase.Warning, m.phase.value)
            activity.emit(Unit)
            runCurrent()
            assertEquals(InactivityPhase.Active, m.phase.value)
            advanceTimeBy(200_000)
            assertEquals(InactivityPhase.Active, m.phase.value)
            assertEquals(listOf(PresenceEvent.WARNED), recorded)
            job.cancel()
        }

    @Test
    fun `activity past the deadline before a tick records locked`() =
        runTest {
            val m = InactivityMonitor(InactivityTimer(240_000, 300_000, 0), { testScheduler.currentTime }, { recorded += it }, 1_000_000)
            val job = m.start(this, activity)
            advanceTimeBy(300_500) // no tick since the start
            activity.emit(Unit)
            runCurrent()
            assertEquals(listOf(PresenceEvent.LOCKED), recorded)
            assertEquals(InactivityPhase.Locked, m.phase.value)
            job.cancel()
        }

    @Test
    fun `warned is recorded before locked when record is slow`() =
        runTest {
            val gate = CompletableDeferred<Unit>()
            val m =
                InactivityMonitor(InactivityTimer(240_000, 300_000, 0), { testScheduler.currentTime }, {
                    gate.await()
                    recorded += it
                })
            val job = m.start(this, activity)
            advanceTimeBy(240_500) // WARNED is now waiting on the gate
            advanceTimeBy(60_000)
            activity.emit(Unit) // past the lock deadline
            gate.complete(Unit)
            runCurrent()
            assertEquals(listOf(PresenceEvent.WARNED, PresenceEvent.LOCKED), recorded)
            job.cancel()
        }

    @Test
    fun `background past lock records only locked`() =
        runTest {
            val m = monitor()
            m.start(this, activity).apply {
                runCurrent()
                cancel()
            }
            advanceTimeBy(400_000) // nothing ticks: the app was in the background
            val late = m.start(this, activity)
            runCurrent()
            assertEquals(listOf(PresenceEvent.LOCKED), recorded)
            late.cancel()
        }

    @Test
    fun `pause holds the timer`() =
        runTest {
            val m = monitor()
            val job = m.start(this, activity)
            advanceTimeBy(100_000)
            m.pause()
            advanceTimeBy(600_000)
            assertEquals(InactivityPhase.Active, m.phase.value)
            m.resume()
            advanceTimeBy(139_000)
            assertEquals(emptyList<PresenceEvent>(), recorded)
            advanceTimeBy(2_000)
            assertEquals(listOf(PresenceEvent.WARNED), recorded)
            job.cancel()
        }

    @Test
    fun `unlock returns to active without recording`() =
        runTest {
            val m = monitor()
            val job = m.start(this, activity)
            advanceTimeBy(301_000)
            assertEquals(InactivityPhase.Locked, m.phase.value)
            m.unlock()
            assertEquals(InactivityPhase.Active, m.phase.value)
            assertEquals(listOf(PresenceEvent.WARNED, PresenceEvent.LOCKED), recorded)
            job.cancel()
        }
}
