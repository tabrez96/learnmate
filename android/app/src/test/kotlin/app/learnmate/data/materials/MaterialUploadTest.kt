package app.learnmate.data.materials

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import app.learnmate.data.api.ApiError
import app.learnmate.data.api.ApiJson
import app.learnmate.data.api.BUDGET_BODY
import app.learnmate.data.api.createLearnmateApi
import app.learnmate.data.family.FamilyRepository
import app.learnmate.data.settings.FallbackPasswordCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File

class MaterialUploadTest {
    @TempDir
    lateinit var tempDir: File

    private lateinit var server: MockWebServer

    private val materialJson =
        """{"id":11,"subject_id":3,"title":"Chapter 1","kind":"upload","status":"reading","created_at":"2026-01-01T10:00:00Z"}"""

    @BeforeEach
    fun start() {
        server = MockWebServer().apply { start() }
    }

    @AfterEach
    fun stop() {
        server.shutdown()
    }

    private fun api() = createLearnmateApi(server.url("/").toString(), "t")

    private val files =
        listOf(
            UploadFile("notes.pdf", "application/pdf", "%PDF-1.4".toByteArray()),
            UploadFile("page.png", "image/png", byteArrayOf(1, 2, 3)),
        )

    @Test
    fun `upload sends a multipart request with the files`() {
        server.enqueue(MockResponse().setResponseCode(201).setBody(materialJson))
        val material = runBlocking { MaterialRepository(api()).upload(3, files, title = "Chapter 1", chapters = "  ") }
        val request = server.takeRequest()
        val body = request.body.readUtf8()
        assertEquals("POST", request.method)
        assertEquals("/api/v1/subjects/3/materials", request.path)
        assertTrue(request.getHeader("Content-Type")!!.startsWith("multipart/form-data"))
        assertTrue(body.contains("""name="files"; filename="notes.pdf""""))
        assertTrue(body.contains("""name="files"; filename="page.png""""))
        assertTrue(body.contains("Content-Type: application/pdf"))
        assertTrue(body.contains("%PDF-1.4"))
        assertTrue(body.contains("""name="title""""))
        assertTrue(body.contains("Chapter 1"))
        assertFalse(body.contains("""name="chapters""""))
        assertEquals(11L, material.id)
    }

    @Test
    fun `upload budget reached is BudgetReached`() {
        server.enqueue(MockResponse().setResponseCode(409).setBody(BUDGET_BODY))
        assertThrows(ApiError.BudgetReached::class.java) { runBlocking { MaterialRepository(api()).upload(3, files) } }
    }

    @Test
    fun `delete data sends a DELETE with a JSON body`() {
        server.enqueue(MockResponse().setResponseCode(204))
        val job = SupervisorJob()
        val cache =
            FallbackPasswordCache(
                PreferenceDataStoreFactory.create(
                    scope = CoroutineScope(Dispatchers.IO + job),
                    produceFile = { File(tempDir, "settings.preferences_pb") },
                ),
            )
        runBlocking {
            FamilyRepository(api(), cache).deleteAllData("secret-pass")
            job.cancelAndJoin()
        }
        val request = server.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("/api/v1/data", request.path)
        val body = ApiJson.parseToJsonElement(request.body.readUtf8()).jsonObject
        assertEquals(setOf("password"), body.keys)
        assertEquals("secret-pass", body.getValue("password").jsonPrimitive.content)
    }
}
