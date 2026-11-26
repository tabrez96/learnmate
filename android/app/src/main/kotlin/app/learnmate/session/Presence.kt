package app.learnmate.session

import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import app.learnmate.data.api.ApiError
import app.learnmate.data.presence.PresenceEvent
import app.learnmate.data.presence.PresenceRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/** While a session runs: tells the server when the app goes to the background and back, and sends a heartbeat. */
class Presence(
    private val sessionId: Long,
    private val repository: PresenceRepository,
    private val scope: CoroutineScope,
    private val heartbeatEveryMs: Long = 15_000,
) : DefaultLifecycleObserver {
    private val _serverState = MutableStateFlow<String?>(null)

    /** The state from the last heartbeat. */
    val serverState: StateFlow<String?> = _serverState

    private var heartbeat: Job? = null
    private var wasStopped = false

    override fun onStart(owner: LifecycleOwner) {
        if (wasStopped) scope.launch { repository.record(sessionId, PresenceEvent.BACK) }
        if (heartbeat?.isActive != true) heartbeat = scope.launch { heartbeatLoop() }
    }

    override fun onStop(owner: LifecycleOwner) {
        wasStopped = true
        heartbeat?.cancel()
        heartbeat = null
        scope.launch { repository.record(sessionId, PresenceEvent.LEFT) }
    }

    /** The caller also removes the observer. */
    fun stop() {
        heartbeat?.cancel()
        heartbeat = null
    }

    private suspend fun heartbeatLoop() {
        while (currentCoroutineContext().isActive) {
            try {
                _serverState.value = repository.heartbeat(sessionId)
                repository.flushIfPending()
            } catch (_: ApiError.Conflict) {
                return // the session is over
            } catch (_: ApiError.NotFound) {
                return
            } catch (_: ApiError) {
                // The server's watchdog reports the silence; try again next tick.
            }
            delay(heartbeatEveryMs)
        }
    }
}
