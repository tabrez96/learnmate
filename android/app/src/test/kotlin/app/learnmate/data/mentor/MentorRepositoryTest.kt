package app.learnmate.data.mentor

import app.learnmate.data.api.AnswerRequestDto
import app.learnmate.data.api.ApiError
import app.learnmate.data.api.BUDGET_BODY
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.MessageRequestDto
import app.learnmate.data.api.httpError
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class MentorRepositoryTest {
    private val api = FakeLearnmateApi()
    private val repo = MentorRepository(api)

    @Test
    fun `lesson returns the lesson`() {
        assertEquals(api.lesson, runBlocking { repo.lesson(7) })
    }

    @Test
    fun `lesson maps budget_reached`() {
        api.failures["startLesson"] = httpError(409, BUDGET_BODY)
        assertThrows(ApiError.BudgetReached::class.java) { runBlocking { repo.lesson(7) } }
    }

    @Test
    fun `answerCheck sends the answer index`() {
        assertEquals(api.checkResult, runBlocking { repo.answerCheck(7, 0, 2) })
        assertEquals(listOf<Any>(AnswerRequestDto(2)), api.bodies)
    }

    @Test
    fun `ask sends books mode by default and outside when asked`() {
        runBlocking {
            repo.ask(7, "Why?")
            repo.ask(7, "Why?", outside = true)
        }
        assertEquals(listOf<Any>(MessageRequestDto("Why?", "books"), MessageRequestDto("Why?", "outside")), api.bodies)
    }

    @Test
    fun `messages returns the history`() {
        assertEquals(api.messages, runBlocking { repo.messages(7) })
    }

    @Test
    fun `answering twice is Conflict`() {
        api.failures["answerLessonCheck"] = httpError(409, """{"detail":"Already answered"}""")
        assertThrows(ApiError.Conflict::class.java) { runBlocking { repo.answerCheck(7, 0, 1) } }
    }
}
