package app.learnmate.data.session

import androidx.room.withTransaction
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.db.OutboxEventEntity
import app.learnmate.data.presence.END_FALLBACK
import app.learnmate.data.presence.END_PIN
import app.learnmate.data.presence.OutboxScheduler
import app.learnmate.data.settings.FallbackPasswordCache
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.Instant

/** Ends a session while the server is unreachable: checks against the cached hashes and queues the end for later. */
class OfflineEndRepository(
    private val database: LearnmateDatabase,
    private val fallback: FallbackPasswordCache,
    private val scheduler: OutboxScheduler,
    private val now: () -> Instant = Instant::now,
) {
    /** True when the PIN matches the cached hash: the session is marked ended here and the end is queued. */
    suspend fun endWithPin(
        sessionId: Long,
        pin: String,
    ): Boolean {
        val row = database.sessionDao().get()?.takeIf { it.id == sessionId } ?: return false
        val hash = row.pinHash ?: return false
        if (!withContext(Dispatchers.Default) { SecretHasher.verify(pin, hash) }) return false
        queue(sessionId, END_PIN, pin, "ended")
        return true
    }

    /** Same with the cached fallback password hash; marks the session force-ended. */
    suspend fun forceEnd(
        sessionId: Long,
        password: String,
    ): Boolean {
        database.sessionDao().get()?.takeIf { it.id == sessionId } ?: return false
        if (!fallback.verify(password)) return false
        queue(sessionId, END_FALLBACK, password, "force_ended")
        return true
    }

    private suspend fun queue(
        sessionId: Long,
        type: String,
        secret: String,
        state: String,
    ) {
        val at = now()
        // One transaction: the queued end and the local state change together or not at all.
        database.withTransaction {
            database.outboxDao().insert(OutboxEventEntity(sessionId = sessionId, type = type, at = at.toString(), secret = secret))
            database.sessionDao().updateState(sessionId, state, at.toEpochMilli())
        }
        scheduler.schedule()
    }
}
