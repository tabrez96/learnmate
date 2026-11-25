package app.learnmate.slice

import android.content.Context
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.learnmate.data.api.ChapterDto
import app.learnmate.data.api.EndDto
import app.learnmate.data.api.EndRequestDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.FamilyRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.SessionRequestDto
import app.learnmate.data.api.SessionWithPinDto
import app.learnmate.data.api.httpError
import app.learnmate.data.api.materialDto
import app.learnmate.data.api.sessionDto
import app.learnmate.data.api.sessionWithPin
import app.learnmate.data.api.subjectDto
import app.learnmate.data.budget.BudgetRepository
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.family.FamilyRepository
import app.learnmate.data.materials.MaterialRepository
import app.learnmate.data.materials.UploadFile
import app.learnmate.data.session.SessionRepository
import app.learnmate.data.settings.FallbackPasswordCache
import app.learnmate.data.subjects.SubjectRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.nio.file.Files

@RunWith(RobolectricTestRunner::class)
class SliceRunnerTest {
    private lateinit var db: LearnmateDatabase
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val api = FakeLearnmateApi()
    private val log = SliceLog()
    private val file = UploadFile("ch1.pdf", "application/pdf", byteArrayOf(1))
    private val ready =
        materialDto(id = 11, status = "ready").copy(
            pagesRead = 5,
            pagesTotal = 5,
            chapters = listOf(ChapterDto(22, "Second", 2), ChapterDto(21, "First", 1)),
        )
    private var pauses = 0
    private val endPins = mutableListOf<String>()
    private val createBodies = mutableListOf<SessionRequestDto>()
    private lateinit var runner: SliceRunner

    @Before
    fun setUp() {
        db =
            Room
                .inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext<Context>(), LearnmateDatabase::class.java)
                .allowMainThreadQueries()
                .build()
        val dir = Files.createTempDirectory("slice").toFile()
        val cache =
            FallbackPasswordCache(
                PreferenceDataStoreFactory.create(scope = scope, produceFile = { dir.resolve("settings.preferences_pb") }),
            )
        // Records the create request and the PIN that ends a session; everything else goes to the fake.
        val recording =
            object : LearnmateApi by api {
                override suspend fun createSession(body: SessionRequestDto): SessionWithPinDto {
                    createBodies += body
                    return api.createSession(body)
                }

                override suspend fun endSession(
                    id: Long,
                    body: EndRequestDto,
                ): EndDto {
                    endPins += body.pin
                    return api.endSession(id, body)
                }
            }
        runner =
            SliceRunner(
                FamilyRepository(recording, cache),
                SubjectRepository(recording),
                MaterialRepository(recording),
                SessionRepository(recording, db.sessionDao()),
                BudgetRepository(recording),
                log,
                pause = {
                    pauses++
                    api.material = ready
                },
                now = { 1_000L },
            )
        api.material = materialDto(id = 11, status = "reading")
    }

    @After
    fun tearDown() {
        db.close()
        scope.cancel()
    }

    @Test
    fun `run uploads, polls, creates and starts`() =
        runBlocking {
            api.withPin = sessionWithPin(id = 9)
            val statuses = mutableListOf<String>()
            val id = runner.run("Science", file) { statuses += it }
            assertEquals(9L, id)
            assertEquals(1, pauses)
            val order = listOf("uploadMaterial", "material", "createSession", "startSession")
            assertEquals(order, api.calls.filter { it in order })
            assertTrue(statuses.contains("Reading: 5/5 pages"))
            assertEquals(listOf("First", "Second"), log.chapters)
            assertEquals("Chapter 1", log.material)
            assertEquals(5, log.pagesRead)
            assertEquals(1.5, log.spentBefore)
            assertEquals(0L, log.readingMillis)
        }

    @Test
    fun `run resets the previous record`() =
        runBlocking {
            log.lesson += LessonEntry("old", emptyList())
            log.answers += AnswerEntry("old?", 1, emptyList(), false)
            log.lessonMillis = 5
            log.spentAfter = 9.0
            runner.run("Science", file) {}
            assertTrue(log.lesson.isEmpty())
            assertTrue(log.answers.isEmpty())
            assertEquals(null, log.lessonMillis)
            assertEquals(null, log.spentAfter)
            assertEquals("Chapter 1", log.material)
        }

    @Test
    fun `run creates a learn session on the material and its chapters`() =
        runBlocking {
            runner.run("Science", file) {}
            val body = createBodies.single()
            assertEquals("learn", body.type)
            assertEquals(listOf(11L), body.materialIds)
            assertEquals(listOf(22L, 21L), body.chapterIds)
        }

    @Test
    fun `reuses a subject with the same name`() =
        runBlocking {
            api.subjects = listOf(subjectDto())
            runner.run(" science ", file) {}
            assertFalse("createSubject" in api.calls)
        }

    @Test
    fun `creates a subject when none matches`() =
        runBlocking {
            runner.run("History", file) {}
            assertTrue("createSubject" in api.calls)
        }

    @Test
    fun `creates the family only when missing`() =
        runBlocking {
            runner.run("Science", file) {}
            assertFalse("putFamily" in api.calls)

            api.failures["family"] = httpError(404, """{"detail":"No family yet"}""")
            runner.run("Science", file) {}
            val body = api.bodies.filterIsInstance<FamilyRequestDto>().single()
            assertEquals(false, body.outsideBooksAllowed)
        }

    @Test
    fun `failed reading stops before the session`() {
        api.material = materialDto(id = 11, status = "failed").copy(error = "bad scan")
        val e = assertThrows(SliceError::class.java) { runBlocking { runner.run("Science", file) {} } }
        assertEquals("Reading failed: bad scan", e.message)
        assertFalse("createSession" in api.calls)
    }

    @Test
    fun `blank subject is rejected before any upload`() {
        assertThrows(SliceError::class.java) { runBlocking { runner.run("  ", file) {} } }
        assertFalse("uploadMaterial" in api.calls)
    }

    @Test
    fun `reading that never finishes gives up`() {
        val stuck = materialDto(id = 11, status = "reading")
        val slow =
            SliceRunner(
                FamilyRepository(
                    api,
                    FallbackPasswordCache(
                        PreferenceDataStoreFactory.create(scope = scope) {
                            Files.createTempDirectory("slice").toFile().resolve("s.preferences_pb")
                        },
                    ),
                ),
                SubjectRepository(api),
                MaterialRepository(api),
                SessionRepository(api, db.sessionDao()),
                BudgetRepository(api),
                log,
                pause = { api.material = stuck },
            )
        api.material = stuck
        val e = assertThrows(SliceError::class.java) { runBlocking { slow.run("Science", file) {} } }
        assertEquals("Still reading after 15 minutes", e.message)
    }

    @Test
    fun `endCurrent uses the pin from this run`() =
        runBlocking {
            api.withPin = sessionWithPin(pin = "1234", id = 9)
            api.session = sessionDto(id = 9, state = "running")
            runner.run("Science", file) {}
            assertTrue(runner.endCurrent())
            assertEquals(listOf("1234"), endPins)
            assertFalse("replacePin" in api.calls)
        }

    @Test
    fun `endCurrent replaces the pin for an unknown session`() =
        runBlocking {
            api.session = sessionDto(id = 5, state = "set_up")
            api.withPin = sessionWithPin(pin = "9876", id = 5)
            assertTrue(runner.endCurrent())
            assertEquals(listOf("replacePin", "endSession"), api.calls.filter { it == "replacePin" || it == "endSession" })
            assertEquals(listOf("9876"), endPins)
        }

    @Test
    fun `endCurrent returns false when there is no session or it already ended`() =
        runBlocking {
            api.failures["currentSession"] = httpError(404, """{"detail":"No session"}""")
            assertFalse(runner.endCurrent())
            api.failures.clear()
            api.session = sessionDto(state = "ended")
            assertFalse(runner.endCurrent())
            assertFalse("endSession" in api.calls)
        }
}
