package app.learnmate.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class PlanStepDto(
    val key: String,
    val kind: String,
    val status: String,
    @SerialName("question_count") val questionCount: Int? = null,
    val topic: String? = null,
    @SerialName("double_points") val doublePoints: Boolean? = null,
)

@Serializable
data class PlanDto(
    @SerialName("session_id") val sessionId: Long,
    @SerialName("test_kind") val testKind: String,
    @SerialName("exam_date") val examDate: String? = null,
    @SerialName("current_step") val currentStep: String? = null,
    val steps: List<PlanStepDto>,
)

@Serializable
data class StepPatchDto(
    val status: String,
)

@Serializable
data class LevelDto(
    val number: Int,
    val title: String,
    @SerialName("next_title") val nextTitle: String,
    val floor: Int,
    @SerialName("next_at") val nextAt: Int,
    @SerialName("to_next") val toNext: Int,
)

@Serializable
data class ProgressDto(
    val points: Int,
    @SerialName("streak_days") val streakDays: Int,
    @SerialName("best_streak_days") val bestStreakDays: Int,
    @SerialName("completed_sessions") val completedSessions: Int,
    val level: LevelDto,
    val badges: List<String> = emptyList(),
    @SerialName("badge_count") val badgeCount: Int,
    @SerialName("completed_challenges") val completedChallenges: Int,
)

@Serializable
data class PassageSourceDto(
    @SerialName("passage_id") val passageId: Long,
    val material: String,
    val chapter: String,
    val page: Int? = null,
)

@Serializable
data class LessonCheckDto(
    val prompt: String,
    val options: List<String>,
    @SerialName("answer_index") val answerIndex: Int? = null,
    @SerialName("correct_index") val correctIndex: Int? = null,
    val explanation: String? = null,
)

@Serializable
data class LessonStepDto(
    val index: Int,
    val title: String,
    val body: String,
    val check: LessonCheckDto,
    val sources: List<PassageSourceDto> = emptyList(),
)

@Serializable
data class LessonDto(
    @SerialName("session_id") val sessionId: Long,
    val topic: String? = null,
    val steps: List<LessonStepDto>,
)

@Serializable
data class AnswerRequestDto(
    @SerialName("answer_index") val answerIndex: Int,
)

@Serializable
data class CheckResultDto(
    val correct: Boolean,
    @SerialName("correct_index") val correctIndex: Int,
    val explanation: String,
    @SerialName("points_awarded") val pointsAwarded: Int,
)

/** No default for [mode]: it is always sent. */
@Serializable
data class MessageRequestDto(
    val text: String,
    val mode: String,
)

@Serializable
data class MessageDto(
    val id: Long,
    val role: String,
    val text: String,
    val sources: List<PassageSourceDto> = emptyList(),
    /** Free-form drawing instructions; a later ticket parses them. */
    val visual: JsonObject? = null,
    val outside: Boolean = false,
    @SerialName("source_url") val sourceUrl: String? = null,
    @SerialName("can_check_outside") val canCheckOutside: Boolean = false,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class PostMessageDto(
    val question: MessageDto,
    val answer: MessageDto,
)

@Serializable
data class TestSourceDto(
    val material: String,
    val chapter: String,
    val page: Int? = null,
)

@Serializable
data class TestQuestionDto(
    val position: Int,
    val prompt: String,
    val options: List<String>,
    @SerialName("answer_index") val answerIndex: Int? = null,
    @SerialName("correct_index") val correctIndex: Int? = null,
    val explanation: String? = null,
    val source: TestSourceDto? = null,
)

@Serializable
data class TestResultDto(
    @SerialName("score_pct") val scorePct: Int,
    val band: String,
    val right: Int,
    val total: Int,
    val points: Int,
    @SerialName("grade_queued") val gradeQueued: Boolean,
)

val UNGRADED_TEST_KINDS = setOf("warmup", "challenge", "bonus")

@Serializable
data class TestDto(
    val id: Long,
    @SerialName("session_id") val sessionId: Long? = null,
    val kind: String,
    val status: String,
    val total: Int,
    @SerialName("current_index") val currentIndex: Int,
    @SerialName("points_so_far") val pointsSoFar: Int,
    val questions: List<TestQuestionDto> = emptyList(),
    val result: TestResultDto? = null,
) {
    /** Warm-up, challenge and bonus are not graded. */
    val graded: Boolean get() = kind !in UNGRADED_TEST_KINDS
    val rightSoFar: Int get() = questions.count { it.answerIndex != null && it.answerIndex == it.correctIndex }
}

@Serializable
data class TestAnswerRequestDto(
    val position: Int,
    @SerialName("answer_index") val answerIndex: Int,
)

@Serializable
data class TestAnswerDto(
    val correct: Boolean,
    @SerialName("correct_index") val correctIndex: Int,
    val explanation: String,
    val source: TestSourceDto? = null,
    @SerialName("points_so_far") val pointsSoFar: Int,
    val finished: Boolean,
    val test: TestDto,
)

@Serializable
data class ChallengeRequestDto(
    val kind: String,
)
