package app.learnmate.data.api

import okhttp3.MediaType.Companion.toMediaType
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
}
