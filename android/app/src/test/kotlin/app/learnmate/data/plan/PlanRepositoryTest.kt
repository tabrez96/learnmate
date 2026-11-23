package app.learnmate.data.plan

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.StepPatchDto
import app.learnmate.data.api.httpError
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class PlanRepositoryTest {
    private val api = FakeLearnmateApi()
    private val repo = PlanRepository(api)

    @Test
    fun `plan returns the server plan`() {
        assertEquals(api.plan, runBlocking { repo.plan(7) })
    }

    @Test
    fun `complete and skip send the status for the key`() {
        runBlocking {
            repo.complete(7, "lesson")
            repo.skip(7, "test")
        }
        assertEquals(listOf<Any>(StepPatchDto("done"), StepPatchDto("skipped")), api.bodies)
        assertEquals(listOf("lesson", "test"), api.stepKeys)
    }

    @Test
    fun `progress returns the server progress`() {
        assertEquals(api.progress, runBlocking { repo.progress() })
    }

    @Test
    fun `unknown session is NotFound`() {
        api.failures["plan"] = httpError(404, """{"detail":"No such session"}""")
        assertThrows(ApiError.NotFound::class.java) { runBlocking { repo.plan(99) } }
    }
}
