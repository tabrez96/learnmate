package app.learnmate.slice

import app.learnmate.data.api.PassageSourceDto
import java.util.Locale

data class SourceRef(
    val material: String,
    val page: Int?,
) {
    override fun toString() = "$material p.${page ?: "?"}"
}

data class LessonEntry(
    val title: String,
    val sources: List<SourceRef>,
)

data class AnswerEntry(
    val question: String,
    val millis: Long,
    val sources: List<SourceRef>,
    val outside: Boolean,
    /** Error class name when the call threw. */
    val failed: String? = null,
) {
    val refused: Boolean get() = failed == null && !outside && sources.isEmpty()
}

fun List<PassageSourceDto>.refs() = map { SourceRef(it.material, it.page) }

/** In-memory record of one slice run. All writes happen on the main dispatcher, so nothing is synchronised. */
class SliceLog {
    var material: String? = null
    var pagesTotal: Int? = null
    var pagesRead: Int = 0
    var chapters: List<String> = emptyList()
    var readingMillis: Long? = null
    var lessonMillis: Long? = null
    var spentBefore: Double? = null
    var spentAfter: Double? = null
    val lesson = mutableListOf<LessonEntry>()
    val answers = mutableListOf<AnswerEntry>()

    val cost: Double?
        get() {
            val before = spentBefore
            val after = spentAfter
            return if (before != null && after != null) after - before else null
        }

    fun reset() {
        material = null
        pagesTotal = null
        pagesRead = 0
        chapters = emptyList()
        readingMillis = null
        lessonMillis = null
        spentBefore = null
        spentAfter = null
        lesson.clear()
        answers.clear()
    }

    fun toMarkdown(): String =
        buildString {
            appendLine("## Material")
            if (material == null) {
                appendLine("Not recorded")
            } else {
                appendLine("- File: ${cell(material!!)}")
                appendLine("- Pages read: $pagesRead of ${pagesTotal ?: "?"}")
                appendLine("- Chapters found: ${chapters.joinToString("; ")}")
                appendLine("- Time to ready: ${seconds(readingMillis)} s")
            }
            appendLine()
            appendLine("## Lesson")
            if (lesson.isEmpty()) {
                appendLine("Not recorded")
            } else {
                appendLine("Generated in ${seconds(lessonMillis)} s.")
                appendLine("| Step | Title | Sources |")
                appendLine("| ---- | ----- | ------- |")
                lesson.forEachIndexed { i, e -> appendLine("| ${i + 1} | ${cell(e.title)} | ${cell(e.sources.joinToString(", "))} |") }
            }
            appendLine()
            appendLine("## Questions")
            if (answers.isEmpty()) {
                appendLine("Not recorded")
            } else {
                appendLine("| # | Question | Answer source | Time (s) | Expected | Verdict | Likely cause |")
                appendLine("| - | -------- | ------------- | -------- | -------- | ------- | ------------ |")
                answers.forEachIndexed { i, a ->
                    appendLine("| ${i + 1} | ${cell(a.question)} | ${sourceText(a)} | ${seconds(a.millis)} |  |  |  |")
                }
            }
            appendLine()
            appendLine("## AI cost")
            appendLine("- Spent before: ${dollars(spentBefore)}")
            appendLine("- Spent after: ${dollars(spentAfter)}")
            appendLine("- This run: ${dollars(cost)}")
        }

    private fun sourceText(a: AnswerEntry) =
        when {
            a.failed != null -> "error: ${a.failed}"
            a.outside -> "outside"
            a.refused -> "refused"
            else -> cell(a.sources.joinToString(", "))
        }

    private fun cell(text: String) = text.replace("|", "\\|").replace("\n", " ")

    private fun seconds(millis: Long?) = millis?.let { "%.1f".format(Locale.ROOT, it / 1000.0) } ?: "Not recorded"

    private fun dollars(value: Double?) = value?.let { "$" + "%.4f".format(Locale.ROOT, it) } ?: "Not recorded"
}
