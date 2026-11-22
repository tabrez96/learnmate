package app.learnmate.data.presence

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.sessionWithPin
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.session.SessionRepository
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.time.Instant

@RunWith(RobolectricTestRunner::class)
class PresenceRepositoryTest {
    private lateinit var db: LearnmateDatabase
    private val api = FakeLearnmateApi()
    private var scheduled = 0
    private val at = Instant.parse("2026-01-01T10:00:00Z")
    private lateinit var repo: PresenceRepository

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        repo = PresenceRepository(api, db.outboxDao(), db.sessionDao(), { scheduled++ }, { at })
    }

    @After
    fun tearDown() = db.close()

    @Test
    fun `record queues event and schedules`() =
        runBlocking {
            repo.record(7, PresenceEvent.LEFT)
            val row = db.outboxDao().pending().single()
            assertEquals("left", row.type)
            assertEquals("2026-01-01T10:00:00Z", row.at)
            assertEquals(1, scheduled)
            assertEquals(emptyList<String>(), api.calls)
        }

    @Test
    fun `flushPending schedules delivery`() {
        repo.flushPending()
        assertEquals(1, scheduled)
    }

    @Test
    fun `unlock posts directly with pin and updates state`() =
        runBlocking {
            SessionRepository(api, db.sessionDao()).create(
                app.learnmate.data.api
                    .SessionRequestDto(3, "revision", listOf(), listOf(), 5),
            )
            api.eventState = "active"
            val dto = repo.unlock(7, "4821")
            assertEquals("active", dto.state)
            val (id, body) = api.events.single()
            assertEquals(7L, id)
            assertEquals("unlocked", body.type)
            assertEquals("4821", body.pin)
            assertEquals("active", db.sessionDao().get()!!.state)
            assertEquals(0, db.outboxDao().count())
        }

    @Test
    fun `heartbeat updates cached state`() =
        runBlocking {
            SessionRepository(api, db.sessionDao()).create(
                app.learnmate.data.api
                    .SessionRequestDto(3, "revision", listOf(), listOf(), 5),
            )
            api.heartbeatState = "locked"
            assertEquals("locked", repo.heartbeat(7))
            assertEquals("locked", db.sessionDao().get()!!.state)
        }
}
