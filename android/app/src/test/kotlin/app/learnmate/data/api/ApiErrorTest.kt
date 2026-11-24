package app.learnmate.data.api

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.decodeFromString
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import java.io.IOException

class ApiErrorTest {
    @Test
    fun `budget body maps to BudgetReached whatever the status`() {
        assertEquals(ApiError.BudgetReached("Monthly AI budget reached"), toApiError(409, BUDGET_BODY, null))
        assertEquals(ApiError.BudgetReached("Monthly AI budget reached"), toApiError(402, BUDGET_BODY, null))
    }

    @Test
    fun `summary decodes missed as a boolean`() {
        for (missed in listOf(true, false)) {
            val body = """{"studied_min":20,"missed":$missed,"future_field":1}"""
            assertEquals(missed, ApiJson.decodeFromString<SummaryDto>(body).missed)
        }
    }

    @Test
    fun `401 is Unauthorized`() = assertEquals(ApiError.Unauthorized, toApiError(401, """{"detail":"no"}""", null))

    @Test
    fun `404 keeps the detail`() =
        assertEquals(ApiError.NotFound("Session not found"), toApiError(404, """{"detail":"Session not found"}""", null))

    @Test
    fun `409 without budget is Conflict`() =
        assertEquals(ApiError.Conflict("Session ended"), toApiError(409, """{"detail":"Session ended"}""", null))

    @Test
    fun `403 object detail is WrongPin`() =
        assertEquals(
            ApiError.WrongPin(2, true),
            toApiError(403, """{"detail":{"message":"Wrong PIN","tries_left":2,"fallback_available":true}}""", null),
        )

    @Test
    fun `403 without object detail is Server`() =
        assertEquals(ApiError.Server(403, "Forbidden"), toApiError(403, """{"detail":"Forbidden"}""", null))

    @Test
    fun `423 reads Retry-After`() =
        assertEquals(
            ApiError.PinLocked(120, false),
            toApiError(423, """{"detail":{"message":"locked","fallback_available":false}}""", "120"),
        )

    @Test
    fun `429 is TooSoon`() = assertEquals(ApiError.TooSoon(30, "Slow down"), toApiError(429, """{"detail":"Slow down"}""", "30"))

    @Test
    fun `422 list detail falls back to HTTP code`() =
        assertEquals(ApiError.Invalid("HTTP 422"), toApiError(422, """{"detail":[{"msg":"bad"}]}""", null))

    @Test
    fun `html body is a plain Server error`() {
        assertEquals(ApiError.Server(502, "HTTP 502"), toApiError(502, "<html>Bad gateway</html>", null))
        assertEquals(ApiError.Server(500, "HTTP 500"), toApiError(500, null, null))
    }

    @Test
    fun `apiCall maps HttpException`() {
        val e =
            assertThrows(ApiError.PinLocked::class.java) {
                runBlocking {
                    apiCall<Unit> {
                        throw httpError(423, """{"detail":{"message":"locked","fallback_available":true}}""", mapOf("Retry-After" to "90"))
                    }
                }
            }
        assertEquals(ApiError.PinLocked(90, true), e)
    }

    @Test
    fun `apiCall maps IOException to Network`() {
        val e = assertThrows(ApiError.Network::class.java) { runBlocking { apiCall<Unit> { throw IOException("offline") } } }
        assertEquals("offline", e.reason)
    }
}
