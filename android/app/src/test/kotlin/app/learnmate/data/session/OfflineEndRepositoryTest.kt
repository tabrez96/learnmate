package app.learnmate.data.session

import android.content.Context
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.db.CurrentSessionEntity
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.settings.FallbackPasswordCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File
import java.time.Instant

@RunWith(RobolectricTestRunner::class)
class OfflineEndRepositoryTest {
    @get:Rule
    val tmp = TemporaryFolder()

    private lateinit var db: LearnmateDatabase
    private lateinit var fallback: FallbackPasswordCache
    private lateinit var repo: OfflineEndRepository
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var scheduled = 0
    private val at = Instant.parse("2026-01-01T10:30:00Z")

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        fallback =
            FallbackPasswordCache(
                PreferenceDataStoreFactory.create(scope = scope, produceFile = { File(tmp.root, "settings.preferences_pb") }),
            )
        repo = OfflineEndRepository(db, fallback, { scheduled++ }, { at })
    }

    @After
    fun tearDown() {
        db.close()
        scope.cancel()
    }

    private suspend fun session(
        id: Long = 7,
        pinHash: String? = SecretHasher.hash("4821"),
    ) = db.sessionDao().replaceCurrent(
        CurrentSessionEntity(
            id = id,
            subjectId = 3,
            type = "revision",
            questionCount = 3,
            state = "active",
            pinHash = pinHash,
            pinVersion = 1,
            startedAt = "2026-01-01T10:00:00Z",
            updatedAtMs = 0,
        ),
    )

    @Test
    fun `right PIN queues end_pin with secret and marks ended`() =
        runBlocking {
            session()
            assertTrue(repo.endWithPin(7, "4821"))
            val row = db.outboxDao().pending().single()
            assertEquals("end_pin", row.type)
            assertEquals("4821", row.secret)
            assertEquals("2026-01-01T10:30:00Z", row.at)
            val saved = db.sessionDao().get()!!
            assertEquals("ended", saved.state)
            assertEquals(at.toEpochMilli(), saved.updatedAtMs)
            assertEquals(1, scheduled)
        }

    @Test
    fun `wrong PIN queues nothing`() =
        runBlocking {
            session()
            assertFalse(repo.endWithPin(7, "0000"))
            assertEquals(0, db.outboxDao().count())
            assertEquals("active", db.sessionDao().get()!!.state)
            assertEquals(0, scheduled)
        }

    @Test
    fun `null pinHash returns false`() =
        runBlocking {
            session(pinHash = null)
            assertFalse(repo.endWithPin(7, "4821"))
            assertEquals(0, db.outboxDao().count())
        }

    @Test
    fun `other session id returns false`() =
        runBlocking {
            session()
            fallback.store("correct horse")
            assertFalse(repo.endWithPin(8, "4821"))
            assertFalse(repo.forceEnd(8, "correct horse"))
            assertEquals(0, db.outboxDao().count())
        }

    @Test
    fun `no session cached returns false`() =
        runBlocking {
            assertFalse(repo.endWithPin(7, "4821"))
            assertFalse(repo.forceEnd(7, "x"))
        }

    @Test
    fun `right fallback queues end_fallback and marks force_ended`() =
        runBlocking {
            session()
            fallback.store("correct horse")
            assertTrue(repo.forceEnd(7, "correct horse"))
            val row = db.outboxDao().pending().single()
            assertEquals("end_fallback", row.type)
            assertEquals("correct horse", row.secret)
            assertEquals("force_ended", db.sessionDao().get()!!.state)
            assertEquals(1, scheduled)
        }

    @Test
    fun `wrong fallback queues nothing`() =
        runBlocking {
            session()
            fallback.store("correct horse")
            assertFalse(repo.forceEnd(7, "nope"))
            assertEquals(0, db.outboxDao().count())
        }

    @Test
    fun `no fallback cached returns false`() =
        runBlocking {
            session()
            assertFalse(repo.forceEnd(7, "anything"))
            assertEquals(0, db.outboxDao().count())
        }
}
