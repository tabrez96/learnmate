package app.learnmate.data.presence

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.httpError
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.db.OutboxEventEntity
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.IOException

@RunWith(RobolectricTestRunner::class)
class OutboxSenderTest {
    private lateinit var db: LearnmateDatabase
    private val api = FakeLearnmateApi()
    private lateinit var sender: OutboxSender

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        sender = OutboxSender(api, db.outboxDao())
    }

    @After
    fun tearDown() = db.close()

    private suspend fun queue(vararg types: String) =
        types.forEachIndexed { i, t -> db.outboxDao().insert(OutboxEventEntity(sessionId = 7, type = t, at = "t$i")) }

    @Test
    fun `sends in order and empties`() =
        runBlocking {
            queue("left", "back")
            assertTrue(sender.sendAll())
            assertEquals(listOf("left", "back"), api.events.map { it.second.type })
            assertEquals(0, db.outboxDao().count())
        }

    @Test
    fun `empty outbox succeeds`() = runBlocking { assertTrue(sender.sendAll()) }

    @Test
    fun `network error stops at the first row and keeps everything`() =
        runBlocking {
            queue("left", "back")
            api.failures["postEvent"] = IOException("offline")
            assertFalse(sender.sendAll())
            assertEquals(1, api.calls.size)
            val rows = db.outboxDao().pending()
            assertEquals(listOf("left", "back"), rows.map { it.type })
            assertEquals(listOf(1, 0), rows.map { it.attempts })
        }

    @Test
    fun `server 5xx is retried and 4xx other than 429 is dropped`() =
        runBlocking {
            queue("left")
            api.failures["postEvent"] = httpError(503, "{}")
            assertFalse(sender.sendAll())
            assertEquals(1, db.outboxDao().count())
            api.failures["postEvent"] = httpError(500, "{}")
            assertFalse(sender.sendAll())
            api.failures["postEvent"] = httpError(401, "{}")
            assertFalse(sender.sendAll())
            api.failures["postEvent"] = httpError(429, "{}")
            assertFalse(sender.sendAll())
            assertEquals(1, db.outboxDao().count())
        }

    @Test
    fun `409 row is dropped and the next one is sent`() =
        runBlocking {
            queue("left", "back")
            api.failures["postEvent"] = httpError(409, """{"detail":"Session ended"}""")
            val first = db.outboxDao().pending().first()
            // Fail only the first call.
            val failing = FailOnce(api, httpError(409, """{"detail":"Session ended"}"""))
            assertTrue(OutboxSender(failing, db.outboxDao()).sendAll())
            assertEquals(0, db.outboxDao().count())
            assertEquals(listOf("back"), api.events.map { it.second.type })
            assertEquals("left", first.type)
        }
}

/** Throws [error] on the first postEvent, then delegates to [delegate] (without its failures). */
private class FailOnce(
    private val delegate: FakeLearnmateApi,
    private val error: Throwable,
) : app.learnmate.data.api.LearnmateApi by delegate {
    private var failed = false

    override suspend fun postEvent(
        id: Long,
        body: app.learnmate.data.api.EventRequestDto,
    ): app.learnmate.data.api.EventDto {
        if (!failed) {
            failed = true
            throw error
        }
        delegate.failures.remove("postEvent")
        return delegate.postEvent(id, body)
    }
}
