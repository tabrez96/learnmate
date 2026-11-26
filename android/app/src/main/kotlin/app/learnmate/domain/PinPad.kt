package app.learnmate.domain

import java.time.Instant
import kotlin.math.ceil
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.minutes
import kotlin.time.Duration.Companion.seconds
import kotlin.time.toJavaDuration

/** Mirrors the server defaults in `config.py`: 5 wrong tries lock the pad for 15 minutes, the fallback shows after 3. */
data class PinRules(
    val length: Int = 4,
    val maxWrong: Int = 5,
    val wrongBeforeFallback: Int = 3,
    val lockout: Duration = 15.minutes,
)

data class PinPadState(
    val digits: String = "",
    /** All wrong tries this session, as this device saw them. */
    val wrongCount: Int = 0,
    /** Tries before the pad locks. */
    val triesLeft: Int = 5,
    /** Sticky: once the link shows, it stays for the session. */
    val fallbackAvailable: Boolean = false,
    val lockedUntil: Instant? = null,
    /** Red dots after a wrong try; cleared by the next digit. */
    val showWrong: Boolean = false,
    val rules: PinRules = PinRules(),
) {
    val isComplete: Boolean get() = digits.length == rules.length

    fun isLocked(now: Instant): Boolean = lockedUntil != null && now < lockedUntil

    fun typed(
        digit: Int,
        now: Instant,
    ): PinPadState = if (isLocked(now) || isComplete || digit !in 0..9) this else copy(digits = digits + digit, showWrong = false)

    fun deleted(): PinPadState = copy(digits = digits.dropLast(1))

    /** A wrong try checked on this device (offline). */
    fun wrong(now: Instant): PinPadState {
        val count = wrongCount + 1
        // Judged from the tries left, not the cumulative count: a server lockout also grants a fresh set.
        val locks = triesLeft - 1 <= 0
        return copy(
            digits = "",
            showWrong = true,
            wrongCount = count,
            fallbackAvailable = fallbackAvailable || count >= rules.wrongBeforeFallback,
            // Each lockout gives a fresh set of tries, as on the server.
            lockedUntil = if (locks) now + rules.lockout.toJavaDuration() else lockedUntil,
            triesLeft = if (locks) rules.maxWrong else triesLeft - 1,
        )
    }

    /** From `ApiError.WrongPin`. */
    fun serverWrong(
        triesLeft: Int,
        fallbackAvailable: Boolean,
    ): PinPadState =
        copy(
            digits = "",
            showWrong = true,
            wrongCount = wrongCount + 1,
            triesLeft = triesLeft,
            fallbackAvailable = this.fallbackAvailable || fallbackAvailable,
        )

    /** From `ApiError.PinLocked`. */
    fun serverLocked(
        retryAfterSeconds: Long,
        fallbackAvailable: Boolean,
        now: Instant,
    ): PinPadState =
        copy(
            digits = "",
            lockedUntil = now + retryAfterSeconds.seconds.toJavaDuration(),
            triesLeft = rules.maxWrong,
            fallbackAvailable = this.fallbackAvailable || fallbackAvailable,
        )

    /** After a correct PIN or a network error. */
    fun cleared(): PinPadState = copy(digits = "")
}

sealed interface PinNotice {
    data object None : PinNotice

    data class Wrong(
        val text: String,
    ) : PinNotice

    data class Locked(
        val title: String,
        val text: String,
    ) : PinNotice
}

fun PinPadState.notice(now: Instant): PinNotice {
    if (lockedUntil != null && isLocked(now)) {
        val remaining =
            java.time.Duration
                .between(now, lockedUntil)
                .toMillis()
                .milliseconds
        return PinNotice.Locked(
            "Too many wrong tries.",
            "The pad is locked for ${countdown(remaining)}. The session keeps running, and we told you on Telegram.",
        )
    }
    if (showWrong) {
        val n = triesLeft
        return PinNotice.Wrong(
            "That's not the session PIN. $n ${if (n == 1) "try" else "tries"} left " +
                "before the pad locks for ${rules.lockout.inWholeMinutes} minutes.",
        )
    }
    return PinNotice.None
}

/** `m:ss`, rounded up so a locked pad never shows "0:00". */
fun countdown(remaining: Duration): String {
    val total = ceil(remaining.inWholeMilliseconds / 1000.0).toLong().coerceAtLeast(0)
    return "${total / 60}:${(total % 60).toString().padStart(2, '0')}"
}
