package app.learnmate.data.session

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.api.ApiError
import app.learnmate.data.api.BUDGET_BODY
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.SessionRequestDto
import app.learnmate.data.api.httpError
import app.learnmate.data.api.sessionDto
import app.learnmate.data.api.sessionWithPin
import app.learnmate.data.db.LearnmateDatabase
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.time.Instant

@RunWith(RobolectricTestRunner::class)
class SessionRepositoryTest {
    private lateinit var db: LearnmateDatabase
    private val api = FakeLearnmateApi()
    private lateinit var repo: SessionRepository
    private val request = SessionRequestDto(3, "revision", listOf(1), listOf(2), 5)

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        repo = SessionRepository(api, db.sessionDao()) { 1000L }
    }

    @After
    fun tearDown() = db.close()

    @Test
    fun `create caches hashed pin and version`() =
        runBlocking {
            api.withPin = sessionWithPin("4821", pinVersion = 3)
            val dto = repo.create(request)
            val row = db.sessionDao().get()!!
            assertEquals("4821", dto.pin)
            assertFalse(row.pinHash!!.contains("4821"))
            assertTrue(SecretHasher.verify("4821", row.pinHash!!))
            assertEquals(3, row.pinVersion)
        }

    @Test
    fun `create maps budget_reached and caches nothing`() =
        runBlocking {
            api.failures["createSession"] = httpError(409, BUDGET_BODY)
            try {
                repo.create(request)
                throw AssertionError("expected BudgetReached")
            } catch (e: ApiError.BudgetReached) {
                // expected
            }
            assertNull(db.sessionDao().get())
        }

    @Test
    fun `replacePin updates hash and version, keeps progress`() =
        runBlocking {
            repo.create(request)
            repo.saveProgress(2, 3, 1)
            api.withPin = sessionWithPin("9999", pinVersion = 2)
            repo.replacePin(7)
            val row = db.sessionDao().get()!!
            assertEquals(2, row.pinVersion)
            assertTrue(SecretHasher.verify("9999", row.pinHash!!))
            assertEquals(listOf(2, 3, 1), listOf(row.stepIndex, row.testQuestionIndex, row.testCorrect))
        }

    @Test
    fun `replacePin for a different id leaves only one row`() =
        runBlocking {
            repo.create(request)
            api.withPin = sessionWithPin("9999", id = 8)
            repo.replacePin(8)
            val cached = db.sessionDao().get()!!
            assertEquals(8L, cached.id)
            assertTrue(SecretHasher.verify("9999", cached.pinHash!!))
            assertEquals(
                1,
                db.query("SELECT COUNT(*) FROM current_session", null).use {
                    it.moveToFirst()
                    it.getInt(0)
                },
            )
        }

    @Test
    fun `start updates cached state`() =
        runBlocking {
            repo.create(request)
            api.session = sessionDto(state = "active")
            repo.start(7)
            assertEquals("active", db.sessionDao().get()!!.state)
        }

    @Test
    fun `start with new pin version drops hash`() =
        runBlocking {
            repo.create(request)
            repo.saveProgress(2, 3, 1)
            api.session = sessionDto(state = "active", pinVersion = 2)
            repo.start(7)
            val row = db.sessionDao().get()!!
            assertNull(row.pinHash)
            assertEquals(2, row.pinVersion)
            assertEquals(2, row.stepIndex)
            assertFalse(repo.checkPinOffline("4821"))
        }

    @Test
    fun `refresh 404 clears cache`() =
        runBlocking {
            repo.create(request)
            api.failures["currentSession"] = httpError(404, """{"detail":"No current session"}""")
            assertNull(repo.refresh())
            assertNull(db.sessionDao().get())
        }

    @Test
    fun `refresh propagates other errors`() =
        runBlocking {
            api.failures["currentSession"] = httpError(401, "{}")
            try {
                repo.refresh()
                throw AssertionError("expected Unauthorized")
            } catch (e: ApiError.Unauthorized) {
                // expected
            }
        }

    @Test
    fun `refresh with new pin version drops hash`() =
        runBlocking {
            repo.create(request)
            api.session = sessionDto(pinVersion = 2)
            val row = repo.refresh()!!
            assertNull(row.pinHash)
            assertEquals(2, row.pinVersion)
            assertFalse(repo.checkPinOffline("4821"))
        }

    @Test
    fun `refresh same version keeps hash and progress`() =
        runBlocking {
            repo.create(request)
            repo.saveProgress(2, 3, 1)
            api.session = sessionDto(state = "active")
            val row = repo.refresh()!!
            assertNotNull(row.pinHash)
            assertEquals("active", row.state)
            assertEquals(2, row.stepIndex)
            assertTrue(repo.checkPinOffline("4821"))
        }

    @Test
    fun `refresh keeps the cached test id`() =
        runBlocking {
            repo.create(request)
            db.sessionDao().updateTest(7, 21, 2, 1, 1)
            val row = repo.refresh()!!
            assertEquals(21L, row.testId)
            assertEquals(2, row.testQuestionIndex)
        }

    @Test
    fun `refresh to a different session id leaves only one row`() =
        runBlocking {
            repo.create(request)
            api.session = sessionDto(id = 8)
            val row = repo.refresh()!!
            val cached = db.sessionDao().get()!!
            assertEquals(8L, row.id)
            assertEquals(8L, cached.id)
            assertNull(cached.pinHash)
            assertEquals(
                1,
                db.query("SELECT COUNT(*) FROM current_session", null).use {
                    it.moveToFirst()
                    it.getInt(0)
                },
            )
        }

    @Test
    fun `refresh with no cached row stores a row without hash`() =
        runBlocking {
            val row = repo.refresh()!!
            assertNull(row.pinHash)
            assertEquals(7L, row.id)
        }

    @Test
    fun `end and forceEnd update cached state`() =
        runBlocking {
            repo.create(request)
            repo.end(7, "4821")
            assertEquals("ended", db.sessionDao().get()!!.state)
            db.sessionDao().updateState(7, "active", 1)
            repo.forceEnd(7, "secret", Instant.parse("2026-01-01T10:00:00Z"))
            assertEquals("ended", db.sessionDao().get()!!.state)
        }

    @Test
    fun `resendPin goes through the api`() =
        runBlocking {
            assertEquals("2026-01-01T10:05:00Z", repo.resendPin(7).nextResendAt)
        }

    @Test
    fun `checkPinOffline true, false and no row`() =
        runBlocking {
            assertFalse(repo.checkPinOffline("4821"))
            repo.create(request)
            assertTrue(repo.checkPinOffline("4821"))
            assertFalse(repo.checkPinOffline("0000"))
        }

    @Test
    fun `saveProgress without a row is a no-op`() =
        runBlocking {
            repo.saveProgress(1, 1, 1)
            assertNull(db.sessionDao().get())
        }
}
