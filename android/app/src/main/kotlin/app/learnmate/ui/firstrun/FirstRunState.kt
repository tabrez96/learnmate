package app.learnmate.ui.firstrun

import app.learnmate.domain.StepState

const val MIN_PASSWORD = 8
const val MAX_PASSWORD = 128 // server limit
const val MAX_NAME = 100 // server limit
val Grades = 5..10

const val NETWORK_ERROR = "Couldn't reach the Learnmate server. Check the connection and try again."

data class FirstRunUiState(
    val loading: Boolean = true,
    val loadFailed: Boolean = false,
    val childName: String = "",
    val grade: Int? = null,
    /** The server has a family row. */
    val familySaved: Boolean = false,
    /** Shown while waiting for the parent's /start message. */
    val linkCode: String? = null,
    val telegramConnected: Boolean = false,
    val telegramHandle: String? = null,
    /** The server already has a fallback password. */
    val fallbackSet: Boolean = false,
    val password: String = "",
    val passwordAgain: String = "",
    val busy: Boolean = false,
    val error: String? = null,
) {
    val childValid get() = childName.isNotBlank() && nameError(childName) == null && grade != null
    val passwordReady get() = password.points() in MIN_PASSWORD..MAX_PASSWORD && password == passwordAgain
    val passwordDone get() = fallbackSet || passwordReady
    val canFinish get() = !loading && !busy && childValid && telegramConnected && passwordDone
    val childStep get() = if (familySaved && childValid) StepState.Done else StepState.Current
    val telegramStep
        get() =
            when {
                telegramConnected -> StepState.Done
                childStep == StepState.Done -> StepState.Current
                else -> StepState.Upcoming
            }
    val passwordStep
        get() =
            when {
                fallbackSet -> StepState.Done
                telegramConnected -> StepState.Current
                else -> StepState.Upcoming
            }
}

/** The server counts Unicode code points, not UTF-16 units. */
private fun String.points() = codePointCount(0, length)

fun nameError(name: String): String? = if (name.trim().points() > MAX_NAME) "Use at most 100 characters" else null

/** Shown under the fields; null while the input is fine or not typed yet. */
fun passwordError(
    password: String,
    again: String,
): String? =
    when {
        password.isNotEmpty() && password.points() < MIN_PASSWORD -> "Use at least 8 characters"
        password.points() > MAX_PASSWORD -> "Use at most 128 characters"
        else -> null
    }

fun againError(
    password: String,
    again: String,
): String? = if (again.isNotEmpty() && again != password) "The two passwords don't match" else null

fun connectedLine(handle: String?): String =
    if (handle.isNullOrBlank()) {
        "Connected. Grades, alerts and session PINs arrive here."
    } else {
        "Connected: @$handle. Grades, alerts and session PINs arrive here."
    }

const val CACHE_ERROR = "Saved, but this tablet couldn't keep a copy for offline use."
