package app.learnmate.data.family

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import app.learnmate.data.api.ApiError
import app.learnmate.data.api.DeleteDataRequestDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.FallbackRequestDto
import app.learnmate.data.api.FamilyRequestDto
import app.learnmate.data.api.httpError
import app.learnmate.data.settings.FallbackPasswordCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File

class FamilyRepositoryTest {
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

    @Test
    fun `get returns the family`() =
        runTest {
            assertEquals(api.family, repo.get())
        }

    @Test
    fun `get returns null before setup`() =
        runTest {
            api.failures["family"] = httpError(404, """{"detail":"No family yet"}""")
            assertNull(repo.get())
        }

    @Test
    fun `save sends the request and returns the family`() =
        runTest {
            val request = FamilyRequestDto("Sam", 7, outsideBooksAllowed = true)
            assertEquals(api.family, repo.save(request))
            assertEquals(listOf<Any>(request), api.bodies)
        }

    @Test
    fun `setFallbackPassword caches the hash after the server accepts`() =
        runTest {
            repo.setFallbackPassword("new-pass", "old-pass")
            assertEquals(listOf<Any>(FallbackRequestDto("new-pass", "old-pass")), api.bodies)
            assertTrue(cache.verify("new-pass"))
        }

    @Test
    fun `wrong current password is a 403 and nothing is cached`() =
        runTest {
            api.failures["putFallback"] = httpError(403, """{"detail":"Current password is wrong"}""")
            val error =
                assertThrows(ApiError.Server::class.java) { kotlinx.coroutines.runBlocking { repo.setFallbackPassword("new", "bad") } }
            assertEquals(403, error.code)
            assertEquals("Current password is wrong", error.detail)
            assertFalse(cache.verify("new"))
        }

    @Test
    fun `telegramCode returns the code`() =
        runTest {
            assertEquals("abc123", repo.telegramCode())
        }

    @Test
    fun `deleteAllData sends the password`() =
        runTest {
            repo.deleteAllData("secret")
            assertEquals(listOf<Any>(DeleteDataRequestDto("secret")), api.bodies)
        }

    @Test
    fun `deleteAllData wrong password is 403`() =
        runTest {
            api.failures["deleteData"] = httpError(403, """{"detail":"Wrong password"}""")
            val error = assertThrows(ApiError.Server::class.java) { kotlinx.coroutines.runBlocking { repo.deleteAllData("x") } }
            assertEquals(403, error.code)
        }
}
