package app.learnmate.data.exams

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.ExamPatchDto
import app.learnmate.data.api.ExamRequestDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.httpError
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import java.time.LocalDate

class ExamRepositoryTest {
    private val api = FakeLearnmateApi()
    private val repo = ExamRepository(api)

    @Test
    fun `list passes the subject filter`() {
        assertEquals(api.exams, runBlocking { repo.list(3) })
        assertEquals(listOf<Long?>(3L), api.examQueries)
    }

    @Test
    fun `list without filter passes null`() {
        runBlocking { repo.list() }
        assertEquals(listOf<Long?>(null), api.examQueries)
    }

    @Test
    fun `create sends ISO date`() {
        assertEquals(api.exam, runBlocking { repo.create(3, LocalDate.of(2026, 12, 1)) })
        assertEquals(listOf<Any>(ExamRequestDto(3, "2026-12-01")), api.bodies)
    }

    @Test
    fun `update sends only changed fields`() {
        runBlocking { repo.update(5, date = LocalDate.of(2026, 12, 2)) }
        assertEquals(listOf<Any>(ExamPatchDto(date = "2026-12-02")), api.bodies)
    }

    @Test
    fun `delete calls deleteExam`() {
        runBlocking { repo.delete(5) }
        assertEquals(listOf("deleteExam"), api.calls)
    }

    @Test
    fun `past date is Invalid`() {
        api.failures["createExam"] = httpError(422, """{"detail":"The date is in the past"}""")
        assertThrows(ApiError.Invalid::class.java) { runBlocking { repo.create(3, LocalDate.of(2020, 1, 1)) } }
    }

    @Test
    fun `same day twice is Conflict`() {
        api.failures["createExam"] = httpError(409, """{"detail":"Exam already set for that day"}""")
        assertThrows(ApiError.Conflict::class.java) { runBlocking { repo.create(3, LocalDate.of(2026, 12, 1)) } }
    }
}
