package app.learnmate.session

import android.content.Context
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.httpError
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.presence.PresenceRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.IOException

@RunWith(RobolectricTestRunner::class)
class PresenceTest {
    private lateinit var db: LearnmateDatabase
    private val api = FakeLearnmateApi()
    private lateinit var repo: PresenceRepository
    private lateinit var registry: LifecycleRegistry

    // LifecycleRegistry holds its owner weakly, so the test must keep it reachable.
    private lateinit var owner: LifecycleOwner

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        repo = PresenceRepository(api, db.outboxDao(), db.sessionDao(), { })
        owner =
            object : LifecycleOwner {
                override val lifecycle: Lifecycle get() = registry
            }
        registry = LifecycleRegistry.createUnsafe(owner)
    }

    @After
    fun tearDown() = db.close()

    private suspend fun awaitRows(n: Int) = withTimeout(5_000) { while (db.outboxDao().count() < n) delay(10) }

    private suspend fun awaitHeartbeats(n: Int) = withTimeout(5_000) { while (api.calls.count { it == "heartbeat" } < n) delay(10) }

    private fun CoroutineScope.attach(everyMs: Long = 60_000) = Presence(7, repo, this, everyMs).also { registry.addObserver(it) }

    @Test
    fun `first start writes nothing`() =
        runBlocking {
            val presence = attach()
            registry.currentState = Lifecycle.State.STARTED
            awaitHeartbeats(1)
            assertEquals(0, db.outboxDao().count())
            presence.stop()
        }

    @Test
    fun `ON_STOP writes left to the outbox`() =
        runBlocking {
            val presence = attach()
            registry.currentState = Lifecycle.State.STARTED
            registry.handleLifecycleEvent(Lifecycle.Event.ON_STOP)
            awaitRows(1)
            assertEquals(listOf("left"), db.outboxDao().pending().map { it.type })
            presence.stop()
        }

    @Test
    fun `ON_START after stop writes back`() =
        runBlocking {
            val presence = attach()
            registry.currentState = Lifecycle.State.STARTED
            registry.handleLifecycleEvent(Lifecycle.Event.ON_STOP)
            awaitRows(1)
            registry.handleLifecycleEvent(Lifecycle.Event.ON_START)
            awaitRows(2)
            assertEquals(listOf("left", "back"), db.outboxDao().pending().map { it.type })
            presence.stop()
        }

    @Test
    fun `heartbeat repeats at its interval and keeps the server state`() =
        runBlocking {
            api.heartbeatState = "locked"
            val presence = attach(everyMs = 20)
            registry.currentState = Lifecycle.State.STARTED
            awaitHeartbeats(3)
            assertEquals("locked", presence.serverState.value)
            presence.stop()
        }

    @Test
    fun `heartbeat failures never crash or write to the outbox`() =
        runBlocking {
            api.failures["heartbeat"] = IOException("offline")
            val presence = attach(everyMs = 20)
            registry.currentState = Lifecycle.State.STARTED
            awaitHeartbeats(3)
            assertEquals(0, db.outboxDao().count())
            api.failures["heartbeat"] = httpError(503, "{}")
            val seen = api.calls.size
            withTimeout(5_000) { while (api.calls.size < seen + 2) delay(10) }
            presence.stop()
        }

    @Test
    fun `heartbeat stops on Conflict`() =
        runBlocking {
            api.failures["heartbeat"] = httpError(409, """{"detail":"Session is not running"}""")
            val presence = attach(everyMs = 20)
            registry.currentState = Lifecycle.State.STARTED
            awaitHeartbeats(1)
            delay(200)
            assertEquals(1, api.calls.count { it == "heartbeat" })
            presence.stop()
        }

    @Test
    fun `heartbeat flushes queued events once the server answers`() =
        runBlocking {
            var scheduled = 0
            val counting = PresenceRepository(api, db.outboxDao(), db.sessionDao(), { scheduled++ })
            counting.record(7, app.learnmate.data.presence.PresenceEvent.LEFT)
            scheduled = 0
            val presence = Presence(7, counting, this, 20).also { registry.addObserver(it) }
            registry.currentState = Lifecycle.State.STARTED
            awaitHeartbeats(1)
            withTimeout(5_000) { while (scheduled == 0) delay(10) }
            assertTrue(scheduled >= 1)
            presence.stop()
        }
}
