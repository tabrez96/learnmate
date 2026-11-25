package app.learnmate.slice

import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.LessonDto
import app.learnmate.data.api.MessageRequestDto
import app.learnmate.data.api.PostMessageDto

/** Times the lesson and every mentor answer and records them, with their sources, in the [log]. */
class TimedLearnmateApi(
    private val delegate: LearnmateApi,
    private val log: SliceLog,
    private val now: () -> Long = System::nanoTime,
) : LearnmateApi by delegate {
    override suspend fun startLesson(sessionId: Long): LessonDto {
        val start = now()
        val dto = delegate.startLesson(sessionId)
        // Re-entering S05 calls this again and the server returns the stored lesson: record the first call only.
        if (log.lessonMillis == null) log.lessonMillis = elapsedMs(start)
        if (log.lesson.isEmpty()) dto.steps.forEach { log.lesson += LessonEntry(it.title, it.sources.refs()) }
        return dto
    }

    override suspend fun postMentorMessage(
        sessionId: Long,
        body: MessageRequestDto,
    ): PostMessageDto {
        val start = now()
        try {
            val dto = delegate.postMentorMessage(sessionId, body)
            log.answers += AnswerEntry(body.text, elapsedMs(start), dto.answer.sources.refs(), dto.answer.outside)
            return dto
        } catch (e: Throwable) {
            log.answers += AnswerEntry(body.text, elapsedMs(start), emptyList(), false, failed = e::class.simpleName)
            throw e
        }
    }

    private fun elapsedMs(start: Long) = (now() - start) / 1_000_000
}
