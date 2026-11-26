package app.learnmate.ui.firstrun

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.FallbackRequestDto
import app.learnmate.data.api.FamilyRequestDto
import app.learnmate.data.api.httpError
import app.learnmate.data.family.FamilyRepository
import app.learnmate.data.settings.FallbackPasswordCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class FirstRunControllerTest {
    @TempDir
    lateinit var tempDir: File

    private val job: Job = SupervisorJob()
    private val api = FakeLearnmateApi()

    private val cache by lazy {
        FallbackPasswordCache(
            PreferenceDataStoreFactory.create(
                scope = CoroutineScope(Dispatchers.IO + job),
                produceFile = { File(tempDir, "settings.preferences_pb") },
            ),
        )
    }
    private val repo by lazy { FamilyRepository(api, cache) }

    @AfterEach
    fun stop() = kotlinx.coroutines.runBlocking { job.cancelAndJoin() }

    private fun TestScope.controller() = FirstRunController(repo, backgroundScope)

    private fun setUp(
        telegram: Boolean = false,
        fallback: Boolean = false,
    ) {
        api.family = api.family.copy(telegramConnected = telegram, telegramHandle = "omars_parent", fallbackSet = fallback)
    }

    @Test
    fun `load with no family gives defaults`() =
        runTest {
            api.failures["family"] = httpError(404, """{"detail":"No family yet"}""")
            val c = controller()
            c.load()
            runCurrent()
            assertEquals(FirstRunUiState(loading = false), c.state.value)
        }

    @Test
    fun `load prefills from the server`() =
        runTest {
            setUp(telegram = true)
            val c = controller()
            c.load()
            runCurrent()
            val s = c.state.value
            assertEquals("Sam", s.childName)
            assertEquals(7, s.grade)
            assertTrue(s.familySaved && s.telegramConnected)
            assertEquals("omars_parent", s.telegramHandle)
            assertFalse(s.loading)
        }

    @Test
    fun `load failure shows the network error`() =
        runTest {
            api.failures["family"] = IOException("down")
            val c = controller()
            c.load()
            runCurrent()
            assertTrue(c.state.value.loadFailed)
            assertEquals(NETWORK_ERROR, c.state.value.error)
            assertFalse(c.state.value.loading)
        }

    @Test
    fun `a successful retry clears the earlier load error`() =
        runTest {
            api.failures["family"] = IOException("down")
            val c = controller()
            c.load()
            runCurrent()
            assertEquals(NETWORK_ERROR, c.state.value.error)
            api.failures.remove("family")
            c.load()
            runCurrent()
            assertNull(c.state.value.error)
            assertFalse(c.state.value.loadFailed)
        }

    @Test
    fun `get link code saves the family then asks for a code`() =
        runTest {
            val c = controller()
            c.setName(" Omar ")
            c.setGrade(7)
            c.getLinkCode()
            advanceTimeBy(1)
            assertEquals(listOf("putFamily", "telegramCode"), api.calls)
            assertEquals(FamilyRequestDto("Omar", 7), api.bodies.single())
            assertEquals("abc123", c.state.value.linkCode)
            assertTrue(c.state.value.familySaved)
            assertFalse(c.state.value.busy)
        }

    @Test
    fun `get link code needs a child`() =
        runTest {
            val c = controller()
            c.getLinkCode()
            runCurrent()
            assertTrue(api.calls.isEmpty())
        }

    @Test
    fun `get link code failure shows the network error`() =
        runTest {
            api.failures["telegramCode"] = IOException("down")
            val c = controller()
            c.setName("Omar")
            c.setGrade(7)
            c.getLinkCode()
            advanceTimeBy(1)
            assertEquals(NETWORK_ERROR, c.state.value.error)
            assertFalse(c.state.value.busy)
            assertNull(c.state.value.linkCode)
        }

    @Test
    fun `polling connects, shows the handle and stops`() =
        runTest {
            val c = controller()
            c.setName("Omar")
            c.setGrade(7)
            c.getLinkCode()
            advanceTimeBy(3_500)
            assertFalse(c.state.value.telegramConnected)
            setUp(telegram = true)
            advanceTimeBy(3_000)
            val s = c.state.value
            assertTrue(s.telegramConnected)
            assertEquals("omars_parent", s.telegramHandle)
            assertNull(s.linkCode)
            val calls = api.calls.count { it == "family" }
            advanceTimeBy(10_000)
            assertEquals(calls, api.calls.count { it == "family" })
        }

    @Test
    fun `polling keeps going through errors`() =
        runTest {
            val c = controller()
            c.setName("Omar")
            c.setGrade(7)
            c.getLinkCode()
            api.failures["family"] = IOException("down")
            advanceTimeBy(6_500)
            assertFalse(c.state.value.telegramConnected)
            api.failures.clear()
            setUp(telegram = true)
            advanceTimeBy(3_000)
            assertTrue(c.state.value.telegramConnected)
        }

    @Test
    fun `edits are ignored while finish is running and work again after`() =
        runTest {
            val c = ready()
            c.finish {}
            val before = c.state.value
            assertTrue(before.busy)
            c.setPassword(SAMPLE_OTHER)
            c.setName("Zed")
            c.setGrade(9)
            val s = c.state.value
            assertEquals(SAMPLE_TYPED, s.password)
            assertEquals(before.childName, s.childName)
            assertEquals(before.grade, s.grade)
            repeat(400) {
                runCurrent()
                if (c.state.value.busy) Thread.sleep(25)
            }
            assertFalse(c.state.value.busy)
        }

    private fun TestScope.ready(fallback: Boolean = false): FirstRunController {
        setUp(telegram = true, fallback = fallback)
        val c = controller()
        c.load()
        runCurrent()
        if (!fallback) {
            c.setPassword(SAMPLE_TYPED)
            c.setPasswordAgain(SAMPLE_TYPED)
        }
        api.calls.clear()
        api.bodies.clear()
        return c
    }

    /** The fallback cache writes on a real dispatcher, so keep running the test scheduler until [onDone] fires. */
    private fun TestScope.finishAndWait(c: FirstRunController): Int {
        var done = 0
        c.finish { done++ }
        repeat(400) {
            runCurrent()
            if (done > 0) return done
            Thread.sleep(25)
        }
        return done
    }

    @Test
    fun `finish saves the family then the password then is done`() =
        runTest {
            val c = ready()
            val done = finishAndWait(c)
            assertEquals(listOf("putFamily", "putFallback"), api.calls)
            assertEquals(FallbackRequestDto(SAMPLE_TYPED), api.bodies.last())
            assertEquals(1, done)
            assertTrue(c.state.value.fallbackSet)
            assertEquals("", c.state.value.password)
            assertFalse(c.state.value.busy)
        }

    @Test
    fun `finish skips the password the server already has`() =
        runTest {
            val c = ready(fallback = true)
            val done = finishAndWait(c)
            assertEquals(listOf("putFamily"), api.calls)
            assertEquals(1, done)
        }

    @Test
    fun `finish failure shows the error and`() =
        runTest {
            val c = ready()
            api.failures["putFallback"] = IOException("down")
            var done = 0
            c.finish { done++ }
            runCurrent()
            assertEquals(NETWORK_ERROR, c.state.value.error)
            assertEquals(0, done)
            assertFalse(c.state.value.busy)
            assertFalse(c.state.value.fallbackSet)
        }

    @Test
    fun `finish does nothing while it cannot finish`() =
        runTest {
            val c = ready()
            c.setPasswordAgain(SAMPLE_OTHER)
            var done = 0
            c.finish { done++ }
            runCurrent()
            assertTrue(api.calls.isEmpty())
            assertEquals(0, done)
        }

    @Test
    fun `load of an unlinked family resumes polling`() =
        runTest {
            setUp(telegram = false)
            val c = controller()
            c.load()
            runCurrent()
            assertFalse(c.state.value.telegramConnected)
            setUp(telegram = true)
            advanceTimeBy(3_001)
            assertTrue(c.state.value.telegramConnected)
            assertEquals("omars_parent", c.state.value.telegramHandle)
        }

    @Test
    fun `load of a linked family does not poll`() =
        runTest {
            setUp(telegram = true)
            val c = controller()
            c.load()
            runCurrent()
            api.calls.clear()
            advanceTimeBy(10_000)
            assertTrue(api.calls.isEmpty())
        }

    @Test
    fun `finish keeps the typed password and shows an error when the local copy fails`() =
        runTest {
            val broken =
                object : DataStore<Preferences> {
                    override val data: Flow<Preferences> = emptyFlow()

                    override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
                        throw IOException("disk")
                }
            val c = FirstRunController(FamilyRepository(api, FallbackPasswordCache(broken)), backgroundScope)
            setUp(telegram = true)
            c.load()
            runCurrent()
            c.setPassword(SAMPLE_TYPED)
            c.setPasswordAgain(SAMPLE_TYPED)
            var done = 0
            c.finish { done++ }
            repeat(400) {
                runCurrent()
                if (!c.state.value.busy) return@repeat
                Thread.sleep(25)
            }
            val s = c.state.value
            assertEquals(CACHE_ERROR, s.error)
            assertEquals(0, done)
            assertFalse(s.busy)
            assertTrue(s.fallbackSet)
        }
}
