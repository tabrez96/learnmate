package app.learnmate.data.session

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.EndDto
import app.learnmate.data.api.EndRequestDto
import app.learnmate.data.api.ForceEndRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.ResendDto
import app.learnmate.data.api.SessionDto
import app.learnmate.data.api.SessionRequestDto
import app.learnmate.data.api.SessionWithPinDto
import app.learnmate.data.api.apiCall
import app.learnmate.data.db.CurrentSessionEntity
import app.learnmate.data.db.SessionDao
import kotlinx.coroutines.flow.Flow
import java.time.Instant

class SessionRepository(
    private val api: LearnmateApi,
    private val dao: SessionDao,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    val current: Flow<CurrentSessionEntity?> = dao.observe()

    /** The caller shows the returned PIN to the parent once; only its hash is kept. */
    suspend fun create(request: SessionRequestDto): SessionWithPinDto {
        val dto = apiCall { api.createSession(request) }
        dao.replaceCurrent(entityOf(dto.toSession(), SecretHasher.hash(dto.pin), null))
        return dto
    }

    suspend fun replacePin(id: Long): SessionWithPinDto {
        val dto = apiCall { api.replacePin(id) }
        dao.replaceCurrent(entityOf(dto.toSession(), SecretHasher.hash(dto.pin), dao.get()?.takeIf { it.id == dto.id }))
        return dto
    }

    suspend fun start(id: Long): SessionDto {
        val dto = apiCall { api.startSession(id) }
        mergeIntoCache(dto)
        return dto
    }

    /** Syncs the cache with the server. Returns null (and clears the cache) when there is no current session. */
    suspend fun refresh(): CurrentSessionEntity? {
        val dto =
            try {
                apiCall { api.currentSession() }
            } catch (_: ApiError.NotFound) {
                dao.clear()
                return null
            }
        return mergeIntoCache(dto)
    }

    suspend fun checkPinOffline(pin: String): Boolean = dao.get()?.pinHash?.let { SecretHasher.verify(pin, it) } ?: false

    suspend fun end(
        id: Long,
        pin: String,
    ): EndDto {
        val dto = apiCall { api.endSession(id, EndRequestDto(pin)) }
        dao.updateState(id, dto.session.state, clock())
        return dto
    }

    suspend fun forceEnd(
        id: Long,
        password: String,
        at: Instant?,
    ): EndDto {
        val dto = apiCall { api.forceEnd(id, ForceEndRequestDto(password, at?.toString())) }
        dao.updateState(id, dto.session.state, clock())
        return dto
    }

    suspend fun resendPin(id: Long): ResendDto = apiCall { api.resendPin(id) }

    suspend fun saveProgress(
        stepIndex: Int,
        testQuestionIndex: Int,
        testCorrect: Int,
    ) {
        val row = dao.get() ?: return
        dao.updateProgress(row.id, stepIndex, testQuestionIndex, testCorrect, clock())
    }

    private suspend fun mergeIntoCache(dto: SessionDto): CurrentSessionEntity {
        val existing = dao.get()?.takeIf { it.id == dto.id }
        // A different version means the PIN was replaced elsewhere (e.g. Telegram): the old hash is useless.
        val sameVersion = existing != null && existing.pinVersion == dto.pinVersion
        val entity = entityOf(dto, if (sameVersion) existing?.pinHash else null, existing)
        dao.replaceCurrent(entity)
        return entity
    }

    private fun entityOf(
        dto: SessionDto,
        pinHash: String?,
        progressFrom: CurrentSessionEntity?,
    ) = CurrentSessionEntity(
        id = dto.id,
        subjectId = dto.subjectId,
        type = dto.type,
        questionCount = dto.questionCount,
        state = dto.state,
        pinHash = pinHash,
        pinVersion = dto.pinVersion,
        startedAt = dto.startedAt,
        stepIndex = progressFrom?.stepIndex ?: 0,
        testQuestionIndex = progressFrom?.testQuestionIndex ?: 0,
        testCorrect = progressFrom?.testCorrect ?: 0,
        updatedAtMs = clock(),
    )
}
