package app.learnmate.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class FamilyDto(
    @SerialName("child_name") val childName: String,
    val grade: Int,
    @SerialName("outside_books_allowed") val outsideBooksAllowed: Boolean,
    @SerialName("inactivity_warn_s") val inactivityWarnS: Int,
    @SerialName("inactivity_lock_s") val inactivityLockS: Int,
    @SerialName("telegram_connected") val telegramConnected: Boolean,
    @SerialName("fallback_set") val fallbackSet: Boolean,
    @SerialName("telegram_handle") val telegramHandle: String? = null,
)

@Serializable
data class FamilyRequestDto(
    @SerialName("child_name") val childName: String,
    val grade: Int,
    @SerialName("outside_books_allowed") val outsideBooksAllowed: Boolean? = null,
    @SerialName("inactivity_warn_s") val inactivityWarnS: Int? = null,
    @SerialName("inactivity_lock_s") val inactivityLockS: Int? = null,
)

@Serializable
data class FallbackRequestDto(
    val password: String,
    @SerialName("current_password") val currentPassword: String? = null,
)

@Serializable
data class TelegramCodeDto(
    val code: String,
)

@Serializable
data class DeleteDataRequestDto(
    val password: String,
)
