package app.learnmate.data.api

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import retrofit2.HttpException
import retrofit2.Response

fun httpError(
    code: Int,
    body: String,
    headers: Map<String, String> = emptyMap(),
): HttpException {
    val raw =
        okhttp3.Response
            .Builder()
            .request(
                okhttp3.Request
                    .Builder()
                    .url("http://localhost/")
                    .build(),
            ).protocol(okhttp3.Protocol.HTTP_1_1)
            .code(code)
            .message("error")
            .apply { headers.forEach { (k, v) -> header(k, v) } }
            .build()
    return HttpException(Response.error<Any>(body.toResponseBody("application/json".toMediaType()), raw))
}

const val BUDGET_BODY = """{"error":"budget_reached","detail":"Monthly AI budget reached"}"""

fun sessionDto(
    id: Long = 7,
    state: String = "created",
    pinVersion: Int = 1,
) = SessionDto(
    id = id,
    subjectId = 3,
    type = "revision",
    questionCount = 5,
    state = state,
    pinVersion = pinVersion,
    createdAt = "2026-01-01T10:00:00Z",
)

fun sessionWithPin(
    pin: String = "4821",
    pinVersion: Int = 1,
    state: String = "created",
    id: Long = 7,
) = sessionDto(id = id, state = state, pinVersion = pinVersion).let {
    SessionWithPinDto(
        it.id,
        it.subjectId,
        it.type,
        it.questionCount,
        it.state,
        it.pinVersion,
        it.createdAt,
        pin = pin,
    )
}

fun familyDto() =
    FamilyDto(
        childName = "Sam",
        grade = 7,
        outsideBooksAllowed = false,
        inactivityWarnS = 60,
        inactivityLockS = 120,
        telegramConnected = false,
        fallbackSet = true,
    )

fun subjectDto(id: Long = 3) = SubjectDto(id = id, name = "Science", icon = "science", materialCount = 2)

fun materialDto(
    id: Long = 11,
    status: String = "reading",
) = MaterialDto(
    id = id,
    subjectId = 3,
    title = "Chapter 1",
    kind = "upload",
    status = status,
    createdAt = "2026-01-01T10:00:00Z",
)

fun examDto(id: Long = 5) = ExamDto(id = id, subjectId = 3, subjectName = "Science", date = "2026-12-01")

fun endDto(state: String = "ended") = EndDto(sessionDto(state = state), SummaryDto(studiedMin = 20))

/** Records calls by method name; set [failures] to make a method throw. */
class FakeLearnmateApi : LearnmateApi {
    val calls = mutableListOf<String>()
    val events = mutableListOf<Pair<Long, EventRequestDto>>()
    val failures = mutableMapOf<String, Throwable>()

    var session: SessionDto = sessionDto()
    var withPin: SessionWithPinDto = sessionWithPin()
    var eventState = "active"
    var heartbeatState = "active"
    var budget = BudgetDto("2026-01", 1.5, 10.0, false)
    var family = familyDto()
    var subjects = listOf(subjectDto())
    var subject = subjectDto()
    var material = materialDto()
    var materials = listOf(materialDto())
    var exams = listOf(examDto())
    var exam = examDto()
    var figureBytes = byteArrayOf(1, 2, 3)
    var telegramCodeValue = "abc123"

    /** Request bodies in call order (upload records its parts). */
    val bodies = mutableListOf<Any>()
    val examQueries = mutableListOf<Long?>()

    private fun hit(name: String) {
        calls += name
        failures[name]?.let { throw it }
    }

    override suspend fun createSession(body: SessionRequestDto): SessionWithPinDto {
        hit("createSession")
        return withPin
    }

    override suspend fun currentSession(): SessionDto {
        hit("currentSession")
        return session
    }

    override suspend fun replacePin(id: Long): SessionWithPinDto {
        hit("replacePin")
        return withPin
    }

    override suspend fun startSession(id: Long): SessionDto {
        hit("startSession")
        return session
    }

    override suspend fun endSession(
        id: Long,
        body: EndRequestDto,
    ): EndDto {
        hit("endSession")
        return endDto()
    }

    override suspend fun resendPin(id: Long): ResendDto {
        hit("resendPin")
        return ResendDto("2026-01-01T10:05:00Z")
    }

    override suspend fun forceEnd(
        id: Long,
        body: ForceEndRequestDto,
    ): EndDto {
        hit("forceEnd")
        return endDto()
    }

    override suspend fun postEvent(
        id: Long,
        body: EventRequestDto,
    ): EventDto {
        hit("postEvent")
        events += id to body
        return EventDto(eventState)
    }

    override suspend fun heartbeat(id: Long): HeartbeatDto {
        hit("heartbeat")
        return HeartbeatDto(heartbeatState)
    }

    override suspend fun budget(): BudgetDto {
        hit("budget")
        return budget
    }

    override suspend fun family(): FamilyDto {
        hit("family")
        return family
    }

    override suspend fun putFamily(body: FamilyRequestDto): FamilyDto {
        hit("putFamily")
        bodies += body
        return family
    }

    override suspend fun putFallback(body: FallbackRequestDto) {
        hit("putFallback")
        bodies += body
    }

    override suspend fun telegramCode(): TelegramCodeDto {
        hit("telegramCode")
        return TelegramCodeDto(telegramCodeValue)
    }

    override suspend fun subjects(): List<SubjectDto> {
        hit("subjects")
        return subjects
    }

    override suspend fun createSubject(body: SubjectRequestDto): SubjectDto {
        hit("createSubject")
        bodies += body
        return subject
    }

    override suspend fun patchSubject(
        id: Long,
        body: SubjectPatchDto,
    ): SubjectDto {
        hit("patchSubject")
        bodies += body
        return subject
    }

    override suspend fun deleteSubject(id: Long) {
        hit("deleteSubject")
    }

    override suspend fun uploadMaterial(
        subjectId: Long,
        files: List<MultipartBody.Part>,
        title: RequestBody?,
        chapters: RequestBody?,
    ): MaterialDto {
        hit("uploadMaterial")
        bodies.add(files)
        return material
    }

    override suspend fun addClassroomMaterial(
        subjectId: Long,
        body: ClassroomRequestDto,
    ): MaterialDto {
        hit("addClassroomMaterial")
        bodies += body
        return material
    }

    override suspend fun materials(subjectId: Long): List<MaterialDto> {
        hit("materials")
        return materials
    }

    override suspend fun material(id: Long): MaterialDto {
        hit("material")
        return material
    }

    override suspend fun deleteMaterial(id: Long) {
        hit("deleteMaterial")
    }

    override suspend fun figure(id: Long): ResponseBody {
        hit("figure")
        return figureBytes.toResponseBody("image/png".toMediaType())
    }

    override suspend fun exams(subjectId: Long?): List<ExamDto> {
        hit("exams")
        examQueries += subjectId
        return exams
    }

    override suspend fun createExam(body: ExamRequestDto): ExamDto {
        hit("createExam")
        bodies += body
        return exam
    }

    override suspend fun patchExam(
        id: Long,
        body: ExamPatchDto,
    ): ExamDto {
        hit("patchExam")
        bodies += body
        return exam
    }

    override suspend fun deleteExam(id: Long) {
        hit("deleteExam")
    }

    override suspend fun deleteData(body: DeleteDataRequestDto) {
        hit("deleteData")
        bodies += body
    }
}
