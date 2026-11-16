package app.learnmate.classroomcheck

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.IOException

private const val TOKEN = "tok-123"
private const val COURSES = """{"courses":[{"id":"c1","name":"Maths"}]}"""
private const val WORK = """{"courseWork":[{"id":"w1","title":"Ch 1","materials":[
    {"driveFile":{"driveFile":{"id":"f1","title":"Notes.pdf"}}}]}]}"""
private const val DRIVE = """{"id":"f1","name":"Notes.pdf","mimeType":"application/pdf","size":"10"}"""
private const val FORBIDDEN = """{"error":{"status":"PERMISSION_DENIED","message":"nope"}}"""

private class FakeHttp(
    private val routes: Map<String, HttpResult>,
    private val failure: IOException? = null,
) : GoogleHttp {
    val tokens = mutableListOf<String>()

    override fun get(
        url: String,
        accessToken: String,
    ): HttpResult {
        tokens += accessToken
        failure?.let { throw it }
        return routes.entries.first { url.startsWith(it.key) }.value
    }
}

private const val CLASSROOM = "https://classroom.googleapis.com/v1/courses"
private const val FILES = "https://www.googleapis.com/drive/v3/files/f1"

private fun happyRoutes(drive: HttpResult = HttpResult(200, DRIVE)) =
    mapOf(
        "$CLASSROOM?" to HttpResult(200, COURSES),
        "$CLASSROOM/c1/courseWork" to HttpResult(200, WORK),
        FILES to drive,
    )

class ClassroomCheckRunnerTest {
    @Test
    fun parseCourses_readsIdAndName() {
        val body = """{"courses":[{"id":"1","name":"A"},{"id":"2","name":"B"}]}"""
        assertEquals(listOf(Course("1", "A"), Course("2", "B")), parseCourses(body))
    }

    @Test
    fun parseCourses_missingKeyIsEmpty() {
        assertTrue(parseCourses("{}").isEmpty())
    }

    @Test
    fun parseCourseWork_mapsAllMaterialKinds() {
        val body = """{"courseWork":[{"id":"w","title":"T","materials":[
            {"driveFile":{"driveFile":{"id":"d","title":"Doc"}}},
            {"link":{"url":"http://x"}},
            {"youtubeVideo":{"id":"y","title":"Vid"}},
            {"form":{"formUrl":"http://f","title":"Quiz"}},
            {"mystery":{}}]}]}"""
        val attachments = parseCourseWork(body).single().attachments
        assertEquals(
            listOf(
                Attachment("driveFile", "Doc", "d"),
                Attachment("link", "http://x", "http://x"),
                Attachment("youtubeVideo", "Vid", "y"),
                Attachment("form", "Quiz", "http://f"),
            ),
            attachments,
        )
    }

    @Test
    fun describeHttpError_usesGoogleErrorBody() {
        assertEquals("HTTP 403 PERMISSION_DENIED: nope", describeHttpError(HttpResult(403, FORBIDDEN)))
        assertEquals("HTTP 502: bad gateway", describeHttpError(HttpResult(502, "bad gateway")))
    }

    @Test
    fun run_happyPath_endsOk() {
        val http = FakeHttp(happyRoutes())
        val lines = ClassroomCheckRunner(http).run(TOKEN, REQUIRED_SCOPES)
        assertTrue("- Maths (c1)" in lines)
        assertTrue("- driveFile: Notes.pdf (f1)" in lines)
        assertTrue("Drive: Notes.pdf (application/pdf, 10)" in lines)
        assertEquals("RESULT: OK", lines.last())
        assertTrue(http.tokens.all { it == TOKEN })
    }

    @Test
    fun run_coursesForbidden_blockedAtCourses() {
        val http = FakeHttp(mapOf("$CLASSROOM?" to HttpResult(403, FORBIDDEN)))
        val lines = ClassroomCheckRunner(http).run(TOKEN, REQUIRED_SCOPES)
        assertEquals("RESULT: BLOCKED at courses", lines.last())
        assertTrue(lines.any { "PERMISSION_DENIED" in it })
    }

    @Test
    fun run_driveForbidden_blockedAtDrive() {
        val lines = ClassroomCheckRunner(FakeHttp(happyRoutes(HttpResult(403, FORBIDDEN)))).run(TOKEN, REQUIRED_SCOPES)
        assertEquals("RESULT: BLOCKED at drive", lines.last())
    }

    @Test
    fun run_reportsMissingScopes() {
        val lines = ClassroomCheckRunner(FakeHttp(happyRoutes())).run(TOKEN, listOf(SCOPE_COURSES))
        assertTrue("MISSING scope: $SCOPE_COURSEWORK" in lines)
        assertTrue("MISSING scope: $SCOPE_DRIVE" in lines)
    }

    @Test
    fun run_ioException_reportsNetworkError() {
        val lines = ClassroomCheckRunner(FakeHttp(emptyMap(), IOException("timeout"))).run(TOKEN, REQUIRED_SCOPES)
        assertEquals("RESULT: NETWORK ERROR", lines.last())
    }

    @Test
    fun run_neverContainsToken() {
        val ok = ClassroomCheckRunner(FakeHttp(happyRoutes())).run(TOKEN, REQUIRED_SCOPES)
        val denied = ClassroomCheckRunner(FakeHttp(happyRoutes(HttpResult(403, FORBIDDEN)))).run(TOKEN, REQUIRED_SCOPES)
        assertTrue((ok + denied).none { TOKEN in it })
    }

    @Test
    fun run_linkOnly_driveNotTested() {
        val work = """{"courseWork":[{"id":"w","title":"T","materials":[{"link":{"url":"http://x"}}]}]}"""
        val routes = happyRoutes() + mapOf("$CLASSROOM/c1/courseWork" to HttpResult(200, work))
        val lines = ClassroomCheckRunner(FakeHttp(routes)).run(TOKEN, REQUIRED_SCOPES)
        assertEquals("RESULT: SIGNED IN, Drive not tested", lines.last())
    }

    @Test
    fun run_findsDriveFileInLaterCourse() {
        val courses = """{"courses":[{"id":"c0","name":"Art"},{"id":"c1","name":"Maths"}]}"""
        val work = """{"courseWork":[{"id":"w","title":"T","materials":[{"link":{"url":"http://x"}}]}]}"""
        val routes =
            linkedMapOf(
                "$CLASSROOM?" to HttpResult(200, courses),
                "$CLASSROOM/c0/courseWork" to HttpResult(200, work),
                "$CLASSROOM/c1/courseWork" to HttpResult(200, WORK),
                FILES to HttpResult(200, DRIVE),
            )
        val lines = ClassroomCheckRunner(FakeHttp(routes)).run(TOKEN, REQUIRED_SCOPES)
        assertTrue("Drive: Notes.pdf (application/pdf, 10)" in lines)
        assertEquals("RESULT: OK", lines.last())
    }
}
