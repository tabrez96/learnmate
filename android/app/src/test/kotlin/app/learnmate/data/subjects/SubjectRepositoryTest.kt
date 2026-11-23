package app.learnmate.data.subjects

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.SubjectPatchDto
import app.learnmate.data.api.SubjectRequestDto
import app.learnmate.data.api.httpError
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class SubjectRepositoryTest {
    private val api = FakeLearnmateApi()
    private val repo = SubjectRepository(api)

    @Test
    fun `list returns subjects`() {
        assertEquals(api.subjects, runBlocking { repo.list() })
    }

    @Test
    fun `create sends name and icon`() {
        val created = runBlocking { repo.create("Science", "science") }
        assertEquals(api.subject, created)
        assertEquals(listOf<Any>(SubjectRequestDto("Science", "science")), api.bodies)
    }

    @Test
    fun `update sends only changed fields`() {
        runBlocking { repo.update(3, name = "Physics") }
        assertEquals(listOf<Any>(SubjectPatchDto(name = "Physics")), api.bodies)
    }

    @Test
    fun `delete calls deleteSubject`() {
        runBlocking { repo.delete(3) }
        assertEquals(listOf("deleteSubject"), api.calls)
    }

    @Test
    fun `duplicate name is Conflict`() {
        api.failures["createSubject"] = httpError(409, """{"detail":"A subject with this name already exists"}""")
        val error = assertThrows(ApiError.Conflict::class.java) { runBlocking { repo.create("Science") } }
        assertEquals("A subject with this name already exists", error.detail)
    }
}
