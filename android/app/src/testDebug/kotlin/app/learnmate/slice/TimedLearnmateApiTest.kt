package app.learnmate.slice

import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.MessageRequestDto
import app.learnmate.data.api.PassageSourceDto
import app.learnmate.data.api.PostMessageDto
import app.learnmate.data.api.messageDto
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.IOException

class TimedLearnmateApiTest {
    private val fake = FakeLearnmateApi()
    private val log = SliceLog()
    private val ticks = ArrayDeque(listOf(0L, 1_500_000_000L, 2_000_000_000L, 9_000_000_000L))
    private val timed = TimedLearnmateApi(fake, log) { ticks.removeFirst() }
    private val question = MessageRequestDto("What is light?", "books")

    @Test
    fun `records answer time and sources`() =
        runTest {
            val answer = messageDto(2).copy(sources = listOf(PassageSourceDto(1, "Ch1", "Light", 4)))
            fake.postedMessage = PostMessageDto(messageDto(1, "student"), answer)
            timed.postMentorMessage(7, question)
            val entry = log.answers.single()
            assertEquals(1500, entry.millis)
            assertEquals(listOf(SourceRef("Ch1", 4)), entry.sources)
            assertEquals("What is light?", entry.question)
        }

    @Test
    fun `records a failed question and rethrows`() =
        runTest {
            fake.failures["postMentorMessage"] = IOException()
            assertThrows(IOException::class.java) { kotlinx.coroutines.runBlocking { timed.postMentorMessage(7, question) } }
            val entry = log.answers.single()
            assertEquals("IOException", entry.failed)
            assertEquals(1500, entry.millis)
        }

    @Test
    fun `lesson is recorded once`() =
        runTest {
            val first = timed.startLesson(7)
            timed.startLesson(7)
            assertEquals(first.steps.size, log.lesson.size)
            assertEquals(1500, log.lessonMillis)
            assertEquals(first.steps[0].title, log.lesson[0].title)
        }

    @Test
    fun `other calls pass through`() =
        runTest {
            assertEquals(fake.budget, timed.budget())
            assertTrue("budget" in fake.calls)
        }
}
