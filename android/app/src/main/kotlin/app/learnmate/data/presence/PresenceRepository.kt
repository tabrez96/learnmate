package app.learnmate.data.presence

import app.learnmate.data.api.EventDto
import app.learnmate.data.api.EventRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.apiCall
import app.learnmate.data.db.OutboxDao
import app.learnmate.data.db.OutboxEventEntity
import app.learnmate.data.db.SessionDao
import java.time.Instant

enum class PresenceEvent(
    val wire: String,
) {
    LEFT("left"),
    BACK("back"),
    WARNED("warned"),
    LOCKED("locked"),
}

class PresenceRepository(
    private val api: LearnmateApi,
    private val outboxDao: OutboxDao,
    private val sessionDao: SessionDao,
    private val scheduler: OutboxScheduler,
    private val now: () -> Instant = Instant::now,
) {
    /** Queues the event; the outbox is the only delivery path so events stay in order. */
    suspend fun record(
        sessionId: Long,
        event: PresenceEvent,
        at: Instant = now(),
    ) {
        outboxDao.insert(OutboxEventEntity(sessionId = sessionId, type = event.wire, at = at.toString()))
        scheduler.schedule()
    }

    /** Not queued: it needs the server's answer. */
    suspend fun unlock(
        sessionId: Long,
        pin: String,
    ): EventDto {
        val dto = apiCall { api.postEvent(sessionId, EventRequestDto("unlocked", now().toString(), pin)) }
        sessionDao.updateState(sessionId, dto.state, now().toEpochMilli())
        return dto
    }

    suspend fun heartbeat(sessionId: Long): String {
        val state = apiCall { api.heartbeat(sessionId) }.state
        sessionDao.updateState(sessionId, state, now().toEpochMilli())
        return state
    }

    /** Schedules delivery when rows are waiting, e.g. after the server answers a heartbeat. */
    suspend fun flushIfPending() {
        if (outboxDao.count() > 0) scheduler.schedule()
    }

    /** Sends rows left behind by a killed process. */
    fun flushPending() = scheduler.schedule()
}
