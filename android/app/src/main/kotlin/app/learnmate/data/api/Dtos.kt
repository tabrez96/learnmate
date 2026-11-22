package app.learnmate.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SessionRequestDto(
    @SerialName("subject_id") val subjectId: Long,
    val type: String,
    @SerialName("material_ids") val materialIds: List<Long>,
    @SerialName("chapter_ids") val chapterIds: List<Long>,
    @SerialName("question_count") val questionCount: Int,
)

@Serializable
data class SessionDto(
    val id: Long,
    @SerialName("subject_id") val subjectId: Long? = null,
    val type: String,
    @SerialName("question_count") val questionCount: Int,
    val state: String,
    @SerialName("pin_version") val pinVersion: Int,
    @SerialName("created_at") val createdAt: String,
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("material_ids") val materialIds: List<Long> = emptyList(),
    @SerialName("chapter_ids") val chapterIds: List<Long> = emptyList(),
    @SerialName("wrong_pins") val wrongPins: Int = 0,
    @SerialName("fallback_available") val fallbackAvailable: Boolean = false,
    @SerialName("pin_locked_until") val pinLockedUntil: String? = null,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("end_reason") val endReason: String? = null,
)

/** A session as returned when a PIN is issued; the clear PIN is shown once and never stored. */
@Serializable
data class SessionWithPinDto(
    val id: Long,
    @SerialName("subject_id") val subjectId: Long? = null,
    val type: String,
    @SerialName("question_count") val questionCount: Int,
    val state: String,
    @SerialName("pin_version") val pinVersion: Int,
    @SerialName("created_at") val createdAt: String,
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("material_ids") val materialIds: List<Long> = emptyList(),
    @SerialName("chapter_ids") val chapterIds: List<Long> = emptyList(),
    @SerialName("wrong_pins") val wrongPins: Int = 0,
    @SerialName("fallback_available") val fallbackAvailable: Boolean = false,
    @SerialName("pin_locked_until") val pinLockedUntil: String? = null,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("end_reason") val endReason: String? = null,
    val pin: String,
) {
    fun toSession() =
        SessionDto(
            id,
            subjectId,
            type,
            questionCount,
            state,
            pinVersion,
            createdAt,
            startedAt,
            materialIds,
            chapterIds,
            wrongPins,
            fallbackAvailable,
            pinLockedUntil,
            endedAt,
            endReason,
        )
}

@Serializable
data class EndRequestDto(
    val pin: String,
)

@Serializable
data class ForceEndRequestDto(
    val password: String,
    val at: String? = null,
)

@Serializable
data class TimelineItemDto(
    val type: String,
    val at: String,
)

@Serializable
data class SummaryDto(
    @SerialName("studied_min") val studiedMin: Int,
    @SerialName("score_pct") val scorePct: Int? = null,
    val band: String? = null,
    val missed: Boolean = false,
    val points: Int = 0,
    @SerialName("left_count") val leftCount: Int = 0,
    @SerialName("lock_minutes") val lockMinutes: List<Int> = emptyList(),
    @SerialName("force_ended") val forceEnded: Boolean = false,
    val timeline: List<TimelineItemDto> = emptyList(),
)

@Serializable
data class EndDto(
    val session: SessionDto,
    val summary: SummaryDto,
)

@Serializable
data class ResendDto(
    @SerialName("next_resend_at") val nextResendAt: String,
)

@Serializable
data class EventRequestDto(
    val type: String,
    val at: String? = null,
    val pin: String? = null,
)

@Serializable
data class EventDto(
    val state: String,
    val recorded: Boolean = true,
)

@Serializable
data class HeartbeatDto(
    val state: String,
)

@Serializable
data class BudgetDto(
    val month: String,
    @SerialName("spent_usd") val spentUsd: Double,
    @SerialName("budget_usd") val budgetUsd: Double,
    val reached: Boolean,
)
