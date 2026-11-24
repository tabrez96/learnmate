package app.learnmate.session.mentor

import app.learnmate.data.api.LessonDto
import app.learnmate.data.api.PassageSourceDto
import java.net.URI
import java.time.Instant

const val READY_FOR_TEST = "Ready for your test?"
const val CONNECTION_LOST = "I lost my connection. Your progress is saved."
const val BOOKS_ONLY_FOOTER = "Answers come only from your books."
const val VISUAL_PLACEHOLDER = "I couldn't show the picture, but the answer above still stands."

sealed interface ChatItem {
    val key: String

    /** Mentor bubble. [checkOutsideFor] is the question to re-ask outside the books when the books don't cover it. */
    data class Mentor(
        override val key: String,
        val text: String,
        val source: String?,
        val hasVisual: Boolean = false,
        val checkOutsideFor: String? = null,
    ) : ChatItem

    /** Amber bubble for an answer checked outside the books. */
    data class Outside(
        override val key: String,
        val text: String,
        val source: String?,
        val hasVisual: Boolean = false,
    ) : ChatItem

    data class Student(
        override val key: String,
        val text: String,
    ) : ChatItem

    /** A step's quick check; [answered] is the chosen option, null while open. */
    data class Check(
        override val key: String,
        val stepIndex: Int,
        val prompt: String,
        val options: List<String>,
        val answered: Int? = null,
    ) : ChatItem

    data class ReadyForTest(
        override val key: String,
    ) : ChatItem

    data class ConnectionLost(
        override val key: String,
    ) : ChatItem
}

data class MentorUiState(
    val loading: Boolean = true,
    /** True once the lesson has loaded; chat stays blocked until then so a reload cannot drop pending questions. */
    val ready: Boolean = false,
    val topic: String = "",
    val stepTitles: List<String> = emptyList(),
    val stepIndex: Int = 0,
    val teachingFrom: String? = null,
    val items: List<ChatItem> = emptyList(),
    val typing: Boolean = false,
    val outsideAllowed: Boolean = false,
    val budgetMessage: String? = null,
) {
    val stepLabel: String get() = "Step ${stepIndex + 1} of ${stepTitles.size}"
    val progress: Float get() = if (stepTitles.isEmpty()) 0f else (stepIndex + 1).toFloat() / stepTitles.size
    val currentCheckAnswered: Boolean
        get() = items.filterIsInstance<ChatItem.Check>().lastOrNull { it.stepIndex == stepIndex }?.answered != null
    val canGoNext: Boolean get() = !typing && currentCheckAnswered && stepIndex < stepTitles.lastIndex
}

fun sourceLine(sources: List<PassageSourceDto>): String? =
    sources.firstOrNull()?.let { "From: ${it.material}, ${if (it.page != null) "p.${it.page}" else it.chapter}" }

fun outsideSourceLine(url: String?): String? {
    if (url.isNullOrBlank()) return null
    val host =
        try {
            URI(url).host
        } catch (_: java.net.URISyntaxException) {
            null
        }
    return "Source: " + (host?.removePrefix("www.") ?: url)
}

fun teachingFromLine(lesson: LessonDto): String? =
    lesson.steps
        .firstOrNull()
        ?.sources
        ?.firstOrNull()
        ?.let { "Teaching from: ${it.material}, ${it.chapter}" }

fun checkResultText(
    correct: Boolean,
    points: Int?,
    explanation: String,
): String =
    when {
        !correct -> "Not quite, and that's okay. $explanation"
        points != null && points > 0 -> "Yes! +$points $explanation"
        else -> "Yes! $explanation"
    }

/** Whole minutes since [startedAt] (ISO instant); 0 when it is missing, unparsable or in the future. */
fun elapsedMinutes(
    startedAt: String?,
    nowMs: Long,
): Int {
    val start =
        try {
            startedAt?.let { Instant.parse(it).toEpochMilli() }
        } catch (_: java.time.format.DateTimeParseException) {
            null
        } ?: return 0
    return ((nowMs - start) / 60_000).toInt().coerceAtLeast(0)
}
