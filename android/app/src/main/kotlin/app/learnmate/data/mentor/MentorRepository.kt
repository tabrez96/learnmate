package app.learnmate.data.mentor

import app.learnmate.data.api.AnswerRequestDto
import app.learnmate.data.api.CheckResultDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.LessonDto
import app.learnmate.data.api.MessageDto
import app.learnmate.data.api.MessageRequestDto
import app.learnmate.data.api.PostMessageDto
import app.learnmate.data.api.apiCall

class MentorRepository(
    private val api: LearnmateApi,
) {
    /** Starts the lesson, or returns the one already started. Throws ApiError.BudgetReached when the AI budget is used up. */
    suspend fun lesson(sessionId: Long): LessonDto = apiCall { api.startLesson(sessionId) }

    suspend fun answerCheck(
        sessionId: Long,
        stepIndex: Int,
        answerIndex: Int,
    ): CheckResultDto = apiCall { api.answerLessonCheck(sessionId, stepIndex, AnswerRequestDto(answerIndex)) }

    suspend fun messages(sessionId: Long): List<MessageDto> = apiCall { api.mentorMessages(sessionId) }

    /** [outside] asks the mentor to check outside the books (only when the family allows it). */
    suspend fun ask(
        sessionId: Long,
        text: String,
        outside: Boolean = false,
    ): PostMessageDto = apiCall { api.postMentorMessage(sessionId, MessageRequestDto(text, if (outside) "outside" else "books")) }
}
