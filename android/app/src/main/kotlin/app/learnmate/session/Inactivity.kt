package app.learnmate.session

import app.learnmate.data.presence.PresenceEvent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

enum class InactivityPhase { Active, Warning, Locked }

/** Pure idle timer: the caller passes the time, so tests use a fake clock. */
class InactivityTimer(
    private val warnAfterMs: Long,
    private val lockAfterMs: Long,
    startMs: Long,
) {
    private var lastActivity = startMs
    private var pausedAt: Long? = null
    private var locked = false

    init {
        require(warnAfterMs in 1 until lockAfterMs) { "warn must be below lock" }
    }

    /**
     * Ignored while locked. Activity after the lock deadline but before the next tick locks instead of resetting.
     * Activity while paused counts from the pause, so `resume` doesn't add that time twice.
     */
    fun onActivity(nowMs: Long) {
        if (locked) return
        if (idle(nowMs) >= lockAfterMs) {
            locked = true
            return
        }
        lastActivity = pausedAt ?: nowMs
    }

    /** The mentor is writing: that time doesn't count. */
    fun pause(nowMs: Long) {
        if (pausedAt == null) pausedAt = nowMs
    }

    fun resume(nowMs: Long) {
        val at = pausedAt ?: return
        lastActivity += nowMs - at
        pausedAt = null
    }

    /** Locked is latched until [unlock]. */
    fun phase(nowMs: Long): InactivityPhase {
        if (locked) return InactivityPhase.Locked
        val idle = idle(nowMs)
        return when {
            idle >= lockAfterMs -> InactivityPhase.Locked.also { locked = true }
            idle >= warnAfterMs -> InactivityPhase.Warning
            else -> InactivityPhase.Active
        }
    }

    /** For the countdown on the warning dialog. */
    fun secondsToLock(nowMs: Long): Int {
        val leftMs = (lockAfterMs - idle(nowMs)).coerceAtLeast(0)
        return ((leftMs + 999) / 1000).toInt()
    }

    fun unlock(nowMs: Long) {
        locked = false
        lastActivity = nowMs
        pausedAt = null
    }

    private fun idle(nowMs: Long) = (pausedAt ?: nowMs) - lastActivity
}

/** Ticks the timer once a second and records `warned` and `locked` once each. */
class InactivityMonitor(
    private val timer: InactivityTimer,
    private val clock: () -> Long,
    private val record: suspend (PresenceEvent) -> Unit,
    private val tickMs: Long = 1_000,
) {
    private val _phase = MutableStateFlow(InactivityPhase.Active)
    val phase: StateFlow<InactivityPhase> = _phase
    private val tickLock = Mutex()

    fun start(
        scope: CoroutineScope,
        activity: Flow<Unit>,
    ): Job =
        scope.launch {
            launch {
                activity.collect {
                    timer.onActivity(clock())
                    tick()
                }
            }
            while (isActive) {
                tick()
                delay(tickMs)
            }
        }

    fun pause() = timer.pause(clock())

    fun resume() = timer.resume(clock())

    /** Records nothing: the server's `unlocked` event comes from the PIN check. */
    fun unlock() {
        timer.unlock(clock())
        _phase.value = InactivityPhase.Active
    }

    /** One transition at a time, recording included, so `warned` always reaches the outbox before `locked`. */
    private suspend fun tick() =
        tickLock.withLock {
            val next = timer.phase(clock())
            if (next == _phase.value) return@withLock
            _phase.value = next
            when (next) {
                InactivityPhase.Warning -> record(PresenceEvent.WARNED)
                InactivityPhase.Locked -> record(PresenceEvent.LOCKED)
                InactivityPhase.Active -> Unit
            }
        }
}
