package app.learnmate.data.api

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.intOrNull
import retrofit2.HttpException
import java.io.IOException

sealed class ApiError(
    message: String,
) : Exception(message) {
    data object BudgetReached : ApiError("AI budget reached")

    /** 401 */
    data object Unauthorized : ApiError("Invalid device token")

    /** 404 */
    data class NotFound(
        val detail: String,
    ) : ApiError(detail)

    /** 409 other than a reached budget */
    data class Conflict(
        val detail: String,
    ) : ApiError(detail)

    /** 403 with an object detail */
    data class WrongPin(
        val triesLeft: Int,
        val fallbackAvailable: Boolean,
    ) : ApiError("Wrong PIN")

    /** 423 */
    data class PinLocked(
        val retryAfterSeconds: Long,
        val fallbackAvailable: Boolean,
    ) : ApiError("PIN pad locked")

    /** 429 */
    data class TooSoon(
        val retryAfterSeconds: Long,
        val detail: String,
    ) : ApiError(detail)

    /** 422 */
    data class Invalid(
        val detail: String,
    ) : ApiError(detail)

    /** Anything else. */
    data class Server(
        val code: Int,
        val detail: String,
    ) : ApiError(detail)

    /** The server could not be reached. */
    data class Network(
        val reason: String,
    ) : ApiError(reason)
}

/** Runs an API call and turns HTTP and network failures into [ApiError]s. */
suspend fun <T> apiCall(block: suspend () -> T): T =
    try {
        block()
    } catch (e: HttpException) {
        throw toApiError(e.code(), e.response()?.errorBody()?.string(), e.response()?.headers()?.get("Retry-After"))
    } catch (e: IOException) {
        throw ApiError.Network(e.message ?: "Network error")
    }

internal fun toApiError(
    code: Int,
    body: String?,
    retryAfter: String?,
): ApiError {
    val json: JsonObject? =
        try {
            body?.let { ApiJson.parseToJsonElement(it) as? JsonObject }
        } catch (_: SerializationException) {
            null
        } catch (_: IllegalArgumentException) {
            null
        }
    if ((json?.get("error") as? JsonPrimitive)?.takeIf { it.isString }?.content == "budget_reached") {
        return ApiError.BudgetReached
    }
    val detail: JsonElement? = json?.get("detail")
    val detailObject = detail as? JsonObject
    val detailText =
        (detail as? JsonPrimitive)?.takeIf { it.isString }?.content
            ?: (detailObject?.get("message") as? JsonPrimitive)?.takeIf { it.isString }?.content
            ?: "HTTP $code"
    val retry = retryAfter?.toLongOrNull() ?: 0
    val fallback = (detailObject?.get("fallback_available") as? JsonPrimitive)?.booleanOrNull ?: false
    return when (code) {
        401 -> ApiError.Unauthorized
        403 ->
            if (detailObject != null) {
                ApiError.WrongPin((detailObject["tries_left"] as? JsonPrimitive)?.intOrNull ?: 0, fallback)
            } else {
                ApiError.Server(403, detailText)
            }
        404 -> ApiError.NotFound(detailText)
        409 -> ApiError.Conflict(detailText)
        422 -> ApiError.Invalid(detailText)
        423 -> ApiError.PinLocked(retry, fallback)
        429 -> ApiError.TooSoon(retry, detailText)
        else -> ApiError.Server(code, detailText)
    }
}
