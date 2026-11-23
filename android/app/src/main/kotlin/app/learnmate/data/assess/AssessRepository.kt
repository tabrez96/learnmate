package app.learnmate.data.assess

import app.learnmate.data.api.ChallengeRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.TestAnswerDto
import app.learnmate.data.api.TestAnswerRequestDto
import app.learnmate.data.api.TestDto
import app.learnmate.data.api.apiCall
import app.learnmate.data.db.SessionDao

enum class ChallengeKind(
    val wire: String,
) {
    WARMUP("warmup"),
    CHALLENGE("challenge"),
    BONUS("bonus"),
}

class AssessRepository(
    private val api: LearnmateApi,
    private val dao: SessionDao,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    suspend fun createTest(sessionId: Long): TestDto = apiCall { api.createTest(sessionId) }.also { cache(it) }

    /** The resume read: does not write the cache. */
    suspend fun test(testId: Long): TestDto = apiCall { api.test(testId) }

    suspend fun answer(
        testId: Long,
        position: Int,
        answerIndex: Int,
    ): TestAnswerDto = apiCall { api.answerTest(testId, TestAnswerRequestDto(position, answerIndex)) }.also { cache(it.test) }

    suspend fun challenge(
        sessionId: Long,
        kind: ChallengeKind,
    ): TestDto = apiCall { api.createChallenge(sessionId, ChallengeRequestDto(kind.wire)) }

    /** Keeps a graded test resumable after the app is killed. Ungraded tests never replace it. */
    private suspend fun cache(test: TestDto) {
        if (!test.graded) return
        val row = dao.get() ?: return
        if (row.id != test.sessionId) return
        dao.updateTest(row.id, test.id, test.currentIndex, test.rightSoFar, clock())
    }
}
