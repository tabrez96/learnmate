package app.learnmate.data.budget

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.BudgetDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.httpError
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class BudgetRepositoryTest {
    private val api = FakeLearnmateApi()

    @Test
    fun `returns the parsed budget`() {
        api.budget = BudgetDto("2026-01", 8.0, 10.0, false)
        assertEquals(api.budget, runBlocking { BudgetRepository(api).current() })
    }

    @Test
    fun `401 is Unauthorized`() {
        api.failures["budget"] = httpError(401, """{"detail":"bad token"}""")
        assertThrows(ApiError.Unauthorized::class.java) { runBlocking { BudgetRepository(api).current() } }
    }
}
