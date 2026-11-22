package app.learnmate.data.api

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class ApiClientTest {
    private val body =
        """{"id":1,"type":"revision","question_count":5,"state":"created","pin_version":1,"created_at":"x","extra":1}"""

    private fun server(): MockWebServer =
        MockWebServer().apply {
            enqueue(MockResponse().setBody(body))
            enqueue(MockResponse().setBody(body))
            start()
        }

    @Test
    fun `every request carries the bearer device token`() {
        val server = server()
        val api = createLearnmateApi(server.url("/").toString(), "test-token")
        runBlocking {
            api.currentSession()
            api.currentSession()
        }
        repeat(2) { assertEquals("Bearer test-token", server.takeRequest().getHeader("Authorization")) }
        server.shutdown()
    }

    @Test
    fun `base url gets api v1 prefix`() {
        for (suffix in listOf("", "/")) {
            val server = server()
            val api = createLearnmateApi(server.url("/").toString().trimEnd('/') + suffix, "t")
            val session = runBlocking { api.currentSession() }
            assertEquals(1L, session.id)
            assertEquals("/api/v1/sessions/current", server.takeRequest().path)
            server.shutdown()
        }
    }

    @Test
    fun `apiBaseUrl normalises the trailing slash`() {
        assertEquals("http://h:8000/api/v1/", apiBaseUrl("http://h:8000"))
        assertEquals("http://h:8000/api/v1/", apiBaseUrl("http://h:8000/"))
    }
}
