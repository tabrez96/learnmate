package app.learnmate.data.presence

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.work.Configuration
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.testing.SynchronousExecutor
import androidx.work.testing.WorkManagerTestInitHelper
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.db.LearnmateDatabase
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.IOException

@RunWith(RobolectricTestRunner::class)
class OutboxWorkerTest {
    private val ctx: Context = ApplicationProvider.getApplicationContext()
    private val dbName = "outbox-test.db"

    private fun openDb() = Room.databaseBuilder(ctx, LearnmateDatabase::class.java, dbName).allowMainThreadQueries().build()

    @Before
    fun setUp() {
        ctx.deleteDatabase(dbName)
    }

    @After
    fun tearDown() {
        ctx.deleteDatabase(dbName)
    }

    private fun workInfo() =
        WorkManager
            .getInstance(ctx)
            .getWorkInfosForUniqueWork(OUTBOX_WORK_NAME)
            .get()
            .single()

    /** The worker runs on a background dispatcher, so poll until [condition] holds. */
    private fun await(condition: () -> Boolean) {
        val deadline = System.currentTimeMillis() + 10_000
        while (!condition() && System.currentTimeMillis() < deadline) Thread.sleep(20)
    }

    /** Queues two events, closes the database (process death), then reopens it and schedules delivery. */
    private fun queueThenRestart(api: FakeLearnmateApi): LearnmateDatabase {
        val first = openDb()
        runBlocking {
            val repo = PresenceRepository(FakeLearnmateApi(), first.outboxDao(), first.sessionDao(), {})
            repo.record(7, PresenceEvent.LEFT)
            repo.record(7, PresenceEvent.BACK)
        }
        first.close()

        val db = openDb()
        val sender = OutboxSender(api, db.outboxDao())
        WorkManagerTestInitHelper.initializeTestWorkManager(
            ctx,
            Configuration
                .Builder()
                .setWorkerFactory(LearnmateWorkerFactory { sender })
                .setExecutor(SynchronousExecutor())
                .build(),
        )
        WorkManagerOutboxScheduler { WorkManager.getInstance(ctx) }.schedule()
        return db
    }

    @Test
    fun `survives process death and sends when network returns`() {
        val api = FakeLearnmateApi()
        val db = queueThenRestart(api)

        assertEquals(emptyList<String>(), api.calls)
        assertEquals(WorkInfo.State.ENQUEUED, workInfo().state)

        WorkManagerTestInitHelper.getTestDriver(ctx)!!.setAllConstraintsMet(workInfo().id)

        await { workInfo().state == WorkInfo.State.SUCCEEDED }

        assertEquals(listOf("left", "back"), api.events.map { it.second.type })
        assertEquals(0, runBlocking { db.outboxDao().count() })
        assertEquals(WorkInfo.State.SUCCEEDED, workInfo().state)
        db.close()
    }

    @Test
    fun `retries when delivery fails`() {
        val api = FakeLearnmateApi().apply { failures["postEvent"] = IOException("offline") }
        val db = queueThenRestart(api)

        WorkManagerTestInitHelper.getTestDriver(ctx)!!.setAllConstraintsMet(workInfo().id)

        await { api.calls.isNotEmpty() && workInfo().state == WorkInfo.State.ENQUEUED }

        assertEquals(1, api.calls.size)
        assertEquals(WorkInfo.State.ENQUEUED, workInfo().state)
        assertEquals(2, runBlocking { db.outboxDao().count() })
        db.close()
    }
}
