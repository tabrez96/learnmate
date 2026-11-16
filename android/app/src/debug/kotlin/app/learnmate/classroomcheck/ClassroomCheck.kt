package app.learnmate.classroomcheck

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

const val SCOPE_COURSES = "https://www.googleapis.com/auth/classroom.courses.readonly"
const val SCOPE_COURSEWORK = "https://www.googleapis.com/auth/classroom.coursework.me.readonly"
const val SCOPE_DRIVE = "https://www.googleapis.com/auth/drive.readonly"
val REQUIRED_SCOPES = listOf(SCOPE_COURSES, SCOPE_COURSEWORK, SCOPE_DRIVE)

data class HttpResult(
    val code: Int,
    val body: String,
)

fun interface GoogleHttp {
    fun get(
        url: String,
        accessToken: String,
    ): HttpResult
}

class OkHttpGoogleHttp(
    private val client: OkHttpClient = OkHttpClient(),
) : GoogleHttp {
    override fun get(
        url: String,
        accessToken: String,
    ): HttpResult {
        val request =
            Request
                .Builder()
                .url(url)
                .header("Authorization", "Bearer $accessToken")
                .build()
        client.newCall(request).execute().use { return HttpResult(it.code, it.body?.string().orEmpty()) }
    }
}

data class Course(
    val id: String,
    val name: String,
)

data class Attachment(
    val kind: String,
    val title: String,
    val ref: String,
)

data class CourseWorkItem(
    val id: String,
    val title: String,
    val attachments: List<Attachment>,
)

private fun JsonObject.text(key: String): String? = (this[key] as? JsonElement)?.jsonPrimitive?.contentOrNull

private fun JsonObject.list(key: String): JsonArray = this[key]?.jsonArray ?: JsonArray(emptyList())

private fun JsonObject.obj(key: String): JsonObject? = this[key]?.jsonObject

fun parseCourses(body: String): List<Course> =
    Json
        .parseToJsonElement(body)
        .jsonObject
        .list("courses")
        .map { it.jsonObject }
        .map { Course(it.text("id").orEmpty(), it.text("name").orEmpty()) }

fun parseCourseWork(body: String): List<CourseWorkItem> =
    Json
        .parseToJsonElement(body)
        .jsonObject
        .list("courseWork")
        .map { it.jsonObject }
        .map { work ->
            CourseWorkItem(
                id = work.text("id").orEmpty(),
                title = work.text("title").orEmpty(),
                attachments = work.list("materials").mapNotNull { parseMaterial(it.jsonObject) },
            )
        }

private fun parseMaterial(material: JsonObject): Attachment? {
    material.obj("driveFile")?.obj("driveFile")?.let {
        return Attachment("driveFile", it.text("title").orEmpty(), it.text("id").orEmpty())
    }
    material.obj("link")?.let {
        val url = it.text("url").orEmpty()
        return Attachment("link", it.text("title") ?: url, url)
    }
    material.obj("youtubeVideo")?.let {
        return Attachment("youtubeVideo", it.text("title").orEmpty(), it.text("id").orEmpty())
    }
    material.obj("form")?.let {
        return Attachment("form", it.text("title").orEmpty(), it.text("formUrl").orEmpty())
    }
    return null
}

fun describeHttpError(result: HttpResult): String {
    try {
        val error = Json.parseToJsonElement(result.body).jsonObject.obj("error")
        val status = error?.text("status")
        val message = error?.text("message")
        if (status != null && message != null) return "HTTP ${result.code} $status: $message"
    } catch (_: SerializationException) {
    } catch (_: IllegalArgumentException) {
    }
    return "HTTP ${result.code}: ${result.body.take(200)}"
}

class ClassroomCheckRunner(
    private val http: GoogleHttp,
) {
    fun run(
        accessToken: String,
        grantedScopes: List<String>,
    ): List<String> {
        val lines = mutableListOf("Granted scopes:")
        grantedScopes.sorted().forEach { lines += "- $it" }
        REQUIRED_SCOPES.filter { it !in grantedScopes }.forEach { lines += "MISSING scope: $it" }
        try {
            check(accessToken, lines)
        } catch (e: IOException) {
            lines += "Network error: ${e.javaClass.simpleName}: ${e.message}"
            lines += "RESULT: NETWORK ERROR"
        }
        return lines
    }

    private fun check(
        token: String,
        lines: MutableList<String>,
    ) {
        val coursesResponse =
            http.get("https://classroom.googleapis.com/v1/courses?studentId=me&courseStates=ACTIVE&pageSize=20", token)
        if (coursesResponse.code != 200) {
            lines += "Courses: ${describeHttpError(coursesResponse)}"
            lines += "RESULT: BLOCKED at courses"
            return
        }
        val courses = parseCourses(coursesResponse.body)
        lines += "Courses (${courses.size}):"
        courses.forEach { lines += "- ${it.name} (${it.id})" }
        if (courses.isEmpty()) {
            lines += "No active courses"
            lines += "RESULT: SIGNED IN, no courses to check"
            return
        }
        var requests = 0
        var blocked = 0
        var chosen: Pair<Course, CourseWorkItem>? = null
        for (course in courses.take(5)) {
            val r = http.get("https://classroom.googleapis.com/v1/courses/${course.id}/courseWork?pageSize=20", token)
            requests++
            if (r.code != 200) {
                blocked++
                lines += "Coursework in ${course.name}: ${describeHttpError(r)}"
                continue
            }
            val items = parseCourseWork(r.body).filter { it.attachments.isNotEmpty() }
            val withDrive = items.firstOrNull { item -> item.attachments.any { it.kind == "driveFile" } }
            if (withDrive != null) {
                chosen = course to withDrive
                break
            }
            if (chosen == null && items.isNotEmpty()) chosen = course to items.first()
        }
        val found = chosen?.second?.attachments.orEmpty()
        chosen?.let { (course, item) ->
            lines += "Coursework '${item.title}' in ${course.name}, attachments (${found.size}):"
            found.forEach { lines += "- ${it.kind}: ${it.title} (${it.ref})" }
        }
        if (found.isEmpty()) lines += "No coursework with attachments in the first 5 courses"
        var driveBlocked = false
        var driveTested = false
        found.firstOrNull { it.kind == "driveFile" }?.let { file ->
            val url = "https://www.googleapis.com/drive/v3/files/${file.ref}?fields=id,name,mimeType,size&supportsAllDrives=true"
            val r = http.get(url, token)
            driveTested = true
            if (r.code == 200) {
                val json = Json.parseToJsonElement(r.body).jsonObject
                lines += "Drive: ${json.text("name")} (${json.text("mimeType")}, ${json.text("size") ?: "no size"})"
            } else {
                driveBlocked = true
                lines += "Drive: ${describeHttpError(r)}"
            }
        }
        lines +=
            when {
                blocked == requests -> "RESULT: BLOCKED at coursework"
                driveBlocked -> "RESULT: BLOCKED at drive"
                !driveTested -> "RESULT: SIGNED IN, Drive not tested"
                else -> "RESULT: OK"
            }
    }
}
