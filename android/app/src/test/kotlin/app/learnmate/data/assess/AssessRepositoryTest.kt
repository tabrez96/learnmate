package app.learnmate.data.assess

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.api.ApiError
import app.learnmate.data.api.BUDGET_BODY
import app.learnmate.data.api.ChallengeRequestDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.TestAnswerRequestDto
import app.learnmate.data.api.httpError
import app.learnmate.data.api.testDto
import app.learnmate.data.db.CurrentSessionEntity
import app.learnmate.data.db.LearnmateDatabase
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class AssessRepositoryTest {
    private lateinit var db: LearnmateDatabase
    private val api = FakeLearnmateApi()
    private lateinit var repo: AssessRepository

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        repo = AssessRepository(api, db.sessionDao()) { 1000L }
    }

    @After
    fun tearDown() = db.close()

    private suspend fun insertRow() =
        db.sessionDao().replaceCurrent(
            CurrentSessionEntity(
                id = 7,
                subjectId = 3,
                type = "revision",
                questionCount = 3,
                state = "active",
                pinHash = null,
                pinVersion = 1,
                startedAt = null,
                updatedAtMs = 0,
            ),
        )

    @Test
    fun `createTest caches the test id at index 0`() =
        runBlocking {
            insertRow()
            repo.createTest(7)
            val row = db.sessionDao().get()!!
            assertEquals(21L, row.testId)
            assertEquals(0, row.testQuestionIndex)
            assertEquals(0, row.testCorrect)
        }

    @Test
    fun `answer updates cached test id, index and right count`() =
        runBlocking {
            insertRow()
            repo.answer(21, 0, 1)
            val row = db.sessionDao().get()!!
            assertEquals(21L, row.testId)
            assertEquals(1, row.testQuestionIndex)
            assertEquals(1, row.testCorrect)
            assertEquals(1000L, row.updatedAtMs)
            assertEquals(listOf<Any>(TestAnswerRequestDto(0, 1)), api.bodies)
        }

    @Test
    fun `answer for another session leaves the row alone`() =
        runBlocking {
            insertRow()
            api.testAnswer = api.testAnswer.copy(test = api.testAnswer.test.copy(sessionId = 8))
            repo.answer(21, 0, 1)
            assertNull(db.sessionDao().get()!!.testId)
        }

    @Test
    fun `answer without a row is a no-op`() =
        runBlocking {
            repo.answer(21, 0, 1)
            assertNull(db.sessionDao().get())
        }

    @Test
    fun `ungraded answer leaves the row alone`() =
        runBlocking {
            insertRow()
            api.testAnswer = api.testAnswer.copy(test = testDto(kind = "bonus", currentIndex = 1, answers = listOf(1, null, null)))
            repo.answer(21, 0, 1)
            assertNull(db.sessionDao().get()!!.testId)
        }

    @Test
    fun `failed answer writes nothing`() =
        runBlocking {
            insertRow()
            api.failures["answerTest"] = httpError(409, """{"detail":"Already answered"}""")
            assertThrows(ApiError.Conflict::class.java) { runBlocking { repo.answer(21, 0, 1) } }
            assertNull(db.sessionDao().get()!!.testId)
        }

    @Test
    fun `test reads without caching`() =
        runBlocking {
            insertRow()
            assertEquals(api.test, repo.test(21))
            assertNull(db.sessionDao().get()!!.testId)
        }

    @Test
    fun `challenge sends the kind`() =
        runBlocking {
            assertEquals(api.challenge, repo.challenge(7, ChallengeKind.WARMUP))
            assertEquals(listOf<Any>(ChallengeRequestDto("warmup")), api.bodies)
        }

    @Test
    fun `challenge maps budget_reached`() {
        api.failures["createChallenge"] = httpError(409, BUDGET_BODY)
        assertThrows(ApiError.BudgetReached::class.java) { runBlocking { repo.challenge(7, ChallengeKind.BONUS) } }
    }
}
