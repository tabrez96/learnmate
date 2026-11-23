package app.learnmate.data.materials

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.BUDGET_BODY
import app.learnmate.data.api.ClassroomRequestDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.httpError
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class MaterialRepositoryTest {
    private val api = FakeLearnmateApi()
    private val repo = MaterialRepository(api)
    private val file = UploadFile("notes.pdf", "application/pdf", "%PDF-1.4".toByteArray())

    @Test
    fun `list, get and delete call the API`() {
        assertEquals(api.materials, runBlocking { repo.list(3) })
        assertEquals(api.material, runBlocking { repo.get(11) })
        runBlocking { repo.delete(11) }
        assertEquals(listOf("materials", "material", "deleteMaterial"), api.calls)
    }

    @Test
    fun `upload returns the material`() {
        assertEquals(api.material, runBlocking { repo.upload(3, listOf(file)) })
        assertEquals(listOf("uploadMaterial"), api.calls)
    }

    @Test
    fun `figure returns the image bytes`() {
        assertArrayEquals(byteArrayOf(1, 2, 3), runBlocking { repo.figure(9) })
    }

    @Test
    fun `addFromClassroom sends link, token, title and chapters`() {
        runBlocking { repo.addFromClassroom(3, "https://classroom.google.com/x", "tok", "Notes", "Ch 1") }
        assertEquals(listOf<Any>(ClassroomRequestDto("https://classroom.google.com/x", "tok", "Notes", "Ch 1")), api.bodies)
    }

    @Test
    fun `missing material is NotFound`() {
        api.failures["material"] = httpError(404, """{"detail":"Material not found"}""")
        assertThrows(ApiError.NotFound::class.java) { runBlocking { repo.get(99) } }
    }

    @Test
    fun `budget reached on upload is BudgetReached`() {
        api.failures["uploadMaterial"] = httpError(409, BUDGET_BODY)
        assertThrows(ApiError.BudgetReached::class.java) { runBlocking { repo.upload(3, listOf(file)) } }
    }

    @Test
    fun `budget reached on Classroom import is BudgetReached`() {
        api.failures["addClassroomMaterial"] = httpError(409, BUDGET_BODY)
        assertThrows(ApiError.BudgetReached::class.java) {
            runBlocking { repo.addFromClassroom(3, "https://classroom.google.com/x", "tok") }
        }
    }
}
