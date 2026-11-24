package app.learnmate.session.mentor

import app.learnmate.data.api.BUDGET_BODY
import app.learnmate.data.api.CheckResultDto
import app.learnmate.data.api.FakeLearnmateApi
import app.learnmate.data.api.LessonCheckDto
import app.learnmate.data.api.LessonDto
import app.learnmate.data.api.LessonStepDto
import app.learnmate.data.api.MessageDto
import app.learnmate.data.api.MessageRequestDto
import app.learnmate.data.api.PassageSourceDto
import app.learnmate.data.api.PostMessageDto
import app.learnmate.data.api.httpError
import app.learnmate.data.mentor.MentorRepository
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.IOException

class MentorControllerTest {
    private val api = FakeLearnmateApi()
    private val saved = mutableListOf<Int>()
    private var allowed = true

    private val source = PassageSourceDto(1, "Science notes", "Chapter 4", 32)

    private fun step(
        index: Int,
        answer: Int? = null,
    ) = LessonStepDto(
        index,
        "Step ${index + 1}",
        "Body ${index + 1}",
        LessonCheckDto("Question ${index + 1}?", listOf("A", "B"), answer, if (answer != null) 1 else null, "Because."),
        listOf(source),
    )

    private fun message(
        id: Long,
        role: String,
        text: String,
        outside: Boolean = false,
        canCheck: Boolean = false,
        url: String? = null,
    ) = MessageDto(id, role, text, emptyList(), null, outside, url, canCheck, "2026-01-01T10:00:00Z")

    private fun TestScope.controller(startStep: Int = 0) =
        MentorController(7, startStep, MentorRepository(api), { allowed }, { saved += it }, this)

    private fun twoSteps(vararg answers: Int?) {
        api.lesson = LessonDto(7, "Photosynthesis", answers.mapIndexed { i, a -> step(i, a) })
        api.messages = emptyList()
    }

    private suspend fun TestScope.loaded(
        startStep: Int = 0,
        block: suspend MentorController.() -> Unit = {},
    ) = controller(startStep).also {
        it.load()
        advanceUntilIdle()
        it.block()
        advanceUntilIdle()
    }

    private fun postedModes() = api.bodies.filterIsInstance<MessageRequestDto>().map { it.mode }

    @Test
    fun `load builds the current step's bubble and check`() =
        runTest {
            twoSteps(null, null)
            val state = loaded().state.value
            assertFalse(state.loading)
            assertEquals("Photosynthesis", state.topic)
            assertEquals(listOf("Step 1", "Step 2"), state.stepTitles)
            assertEquals("Teaching from: Science notes, Chapter 4", state.teachingFrom)
            val mentor = state.items[0] as ChatItem.Mentor
            assertEquals("Body 1", mentor.text)
            assertEquals("From: Science notes, p.32", mentor.source)
            assertTrue(state.items[1] is ChatItem.Check)
            assertEquals(2, state.items.size)
        }

    @Test
    fun `load rebuilds answered steps and clamps a cached step`() =
        runTest {
            twoSteps(1, 0)
            val state = loaded(startStep = 9).state.value
            assertEquals(1, state.stepIndex)
            val texts = state.items.map { (it as? ChatItem.Mentor)?.text ?: (it as? ChatItem.Student)?.text }
            assertEquals(
                listOf("Body 1", null, "B", "Yes! Because.", "Body 2", null, "A", "Not quite, and that's okay. Because."),
                texts.take(8),
            )
            assertTrue(state.items.last() is ChatItem.ReadyForTest)
        }

    @Test
    fun `load with no steps does not crash`() =
        runTest {
            api.lesson = LessonDto(7, null, emptyList())
            api.messages = emptyList()
            val state = loaded().state.value
            assertTrue(state.items.isEmpty())
            assertFalse(state.canGoNext)
        }

    @Test
    fun `load replays history after the lesson`() =
        runTest {
            twoSteps(null, null)
            api.messages = listOf(message(1, "student", "Why?"), message(2, "mentor", "Because.", canCheck = true))
            val items = loaded().state.value.items
            assertEquals("Why?", (items[2] as ChatItem.Student).text)
            val reply = items[3] as ChatItem.Mentor
            assertEquals("Because.", reply.text)
            assertEquals("Why?", reply.checkOutsideFor)
        }

    @Test
    fun `history offers no outside check when the setting is off`() =
        runTest {
            allowed = false
            twoSteps(null)
            api.messages = listOf(message(1, "student", "Why?"), message(2, "mentor", "Not covered.", canCheck = true))
            assertNull(
                (
                    loaded()
                        .state.value.items
                        .last() as ChatItem.Mentor
                ).checkOutsideFor,
            )
        }

    @Test
    fun `budget on lesson start sets budgetMessage`() =
        runTest {
            api.failures["startLesson"] = httpError(409, BUDGET_BODY)
            val state = loaded().state.value
            assertEquals("Monthly AI budget reached", state.budgetMessage)
            assertTrue(state.items.none { it is ChatItem.ConnectionLost })
            assertFalse(state.loading)
            assertFalse(state.typing)
        }

    @Test
    fun `budget on ask shows the alert without a connection bubble`() =
        runTest {
            twoSteps(null)
            val c = loaded { send("Why?", false) }
            api.failures["postMentorMessage"] = httpError(409, BUDGET_BODY)
            c.send("Again?", false)
            advanceUntilIdle()
            assertEquals("Monthly AI budget reached", c.state.value.budgetMessage)
            assertTrue(
                c.state.value.items
                    .none { it is ChatItem.ConnectionLost },
            )
        }

    @Test
    fun `plain send uses books mode`() =
        runTest {
            twoSteps(null)
            loaded { send("  Why?  ", false) }
            assertEquals(listOf("books"), postedModes())
            assertEquals(MessageRequestDto("Why?", "books"), api.bodies.last())
        }

    @Test
    fun `send outside uses outside mode then books again`() =
        runTest {
            twoSteps(null)
            loaded {
                send("Why?", true)
                advanceUntilIdle()
                send("And?", false)
            }
            assertEquals(listOf("outside", "books"), postedModes())
        }

    @Test
    fun `send outside is refused when the setting is off`() =
        runTest {
            allowed = false
            twoSteps(null)
            val c = loaded { send("Why?", true) }
            assertTrue(postedModes().isEmpty())
            assertTrue(
                c.state.value.items
                    .none { it is ChatItem.Student },
            )
        }

    @Test
    fun `blank send is ignored`() =
        runTest {
            twoSteps(null)
            loaded { send("   ", false) }
            assertTrue(postedModes().isEmpty())
        }

    @Test
    fun `not covered answer offers check outside`() =
        runTest {
            twoSteps(null)
            api.postedMessage = PostMessageDto(message(1, "student", "Why?"), message(2, "mentor", "Not in your books.", canCheck = true))
            val c = loaded { send("Why?", false) }
            assertEquals(
                "Why?",
                (
                    c.state.value.items
                        .last() as ChatItem.Mentor
                ).checkOutsideFor,
            )
        }

    @Test
    fun `checkOutside posts outside without a student bubble and clears the offer`() =
        runTest {
            twoSteps(null)
            api.postedMessage = PostMessageDto(message(1, "student", "Why?"), message(2, "mentor", "Not in your books.", canCheck = true))
            val c = loaded { send("Why?", false) }
            api.postedMessage =
                PostMessageDto(
                    message(3, "student", "Why?"),
                    message(4, "mentor", "Outside.", outside = true, url = "https://www.britannica.com/x"),
                )
            c.checkOutside("Why?")
            advanceUntilIdle()
            assertEquals(listOf("books", "outside"), postedModes())
            val items = c.state.value.items
            assertEquals(1, items.count { it is ChatItem.Student })
            assertNull(items.filterIsInstance<ChatItem.Mentor>().last { it.text == "Not in your books." }.checkOutsideFor)
            val outside = items.last() as ChatItem.Outside
            assertEquals("Source: britannica.com", outside.source)
        }

    @Test
    fun `checkOutside is refused when the setting is off`() =
        runTest {
            allowed = false
            twoSteps(null)
            loaded { checkOutside("Why?") }
            assertTrue(postedModes().isEmpty())
        }

    @Test
    fun `explainAgain asks about the current step`() =
        runTest {
            twoSteps(null)
            loaded { explainAgain() }
            assertEquals(MessageRequestDto("Can you explain \"Step 1\" again?", "books"), api.bodies.last())
        }

    @Test
    fun `answer appends student choice and result`() =
        runTest {
            twoSteps(null, null)
            val c = loaded { answer(0, 1) }
            val items = c.state.value.items
            assertEquals(1, (items[1] as ChatItem.Check).answered)
            assertEquals("B", (items[2] as ChatItem.Student).text)
            val result = items[3] as ChatItem.Mentor
            assertEquals("Yes! +5 Because.", result.text)
            assertEquals("From: Science notes, p.32", result.source)
            assertTrue(items.none { it is ChatItem.ReadyForTest })
        }

    @Test
    fun `answering twice is ignored`() =
        runTest {
            twoSteps(null)
            loaded {
                answer(0, 1)
                advanceUntilIdle()
                answer(0, 0)
            }
            assertEquals(1, api.bodies.size)
        }

    @Test
    fun `answering the last step adds ReadyForTest`() =
        runTest {
            twoSteps(null)
            val c = loaded { answer(0, 0) }
            assertTrue(
                c.state.value.items
                    .last() is ChatItem.ReadyForTest,
            )
        }

    @Test
    fun `nextStep advances and saves`() =
        runTest {
            twoSteps(null, null)
            val c = loaded { nextStep() }
            assertEquals(0, c.state.value.stepIndex)
            assertTrue(saved.isEmpty())
            c.answer(0, 0)
            advanceUntilIdle()
            c.nextStep()
            advanceUntilIdle()
            assertEquals(1, c.state.value.stepIndex)
            assertEquals(listOf(1), saved)
            assertEquals(
                "Body 2",
                (
                    c.state.value.items
                        .filterIsInstance<ChatItem.Mentor>()
                        .last()
                ).text,
            )
            assertTrue(
                c.state.value.items
                    .last() is ChatItem.Check,
            )
        }

    @Test
    fun `network error adds ConnectionLost and retry re-runs`() =
        runTest {
            twoSteps(null)
            api.checkResult = CheckResultDto(true, 0, "Because.", 5)
            api.failures["answerLessonCheck"] = IOException("down")
            val c = loaded { answer(0, 0) }
            assertTrue(
                c.state.value.items
                    .last() is ChatItem.ConnectionLost,
            )
            assertFalse(c.state.value.typing)
            val failed = c.state.value.items
            assertNull(failed.filterIsInstance<ChatItem.Check>().single().answered)
            assertTrue(failed.none { it is ChatItem.Student })
            assertFalse(c.state.value.canGoNext)
            api.failures.clear()
            c.retry(failed.last().key)
            advanceUntilIdle()
            val items = c.state.value.items
            assertEquals(0, items.filterIsInstance<ChatItem.Check>().single().answered)
            assertTrue(items.none { it is ChatItem.ConnectionLost })
            assertTrue(items.any { (it as? ChatItem.Mentor)?.text == "Yes! +5 Because." })
        }

    @Test
    fun `network error on load retries the whole load`() =
        runTest {
            twoSteps(null)
            api.failures["startLesson"] = IOException("down")
            val c = loaded()
            assertEquals(listOf<ChatItem>(ChatItem.ConnectionLost("i0")), c.state.value.items)
            assertFalse(c.state.value.loading)
            api.failures.clear()
            c.retry("i0")
            advanceUntilIdle()
            assertEquals(
                "Body 1",
                (
                    c.state.value.items
                        .first() as ChatItem.Mentor
                ).text,
            )
        }

    @Test
    fun `chat is blocked until the lesson has loaded`() =
        runTest {
            twoSteps(null)
            api.failures["startLesson"] = IOException("down")
            val c = loaded { send("A?", false) }
            assertFalse(c.state.value.ready)
            assertTrue(postedModes().isEmpty())
            assertEquals(listOf<ChatItem>(ChatItem.ConnectionLost("i0")), c.state.value.items)
            api.failures.clear()
            c.retry("i0")
            advanceUntilIdle()
            assertTrue(c.state.value.ready)
            c.send("A?", false)
            advanceUntilIdle()
            assertEquals(listOf("books"), postedModes())
        }

    @Test
    fun `retry without a failure does nothing`() =
        runTest {
            twoSteps(null)
            val c = loaded { retry("missing") }
            assertEquals(2, c.state.value.items.size)
        }

    @Test
    fun `each connection lost bubble retries its own request`() =
        runTest {
            twoSteps(null)
            val c = loaded()
            api.failures["postMentorMessage"] = IOException("down")
            c.send("A?", false)
            advanceUntilIdle()
            c.send("B?", false)
            advanceUntilIdle()
            val lost =
                c.state.value.items
                    .filterIsInstance<ChatItem.ConnectionLost>()
            assertEquals(2, lost.size)
            api.failures.clear()
            api.postedMessage = PostMessageDto(message(1, "student", "A?"), message(2, "mentor", "Answer A."))
            c.retry(lost[0].key)
            advanceUntilIdle()
            assertEquals(
                listOf(lost[1].key),
                c.state.value.items
                    .filterIsInstance<ChatItem.ConnectionLost>()
                    .map { it.key },
            )
            assertEquals(MessageRequestDto("A?", "books"), api.bodies.last())
        }

    @Test
    fun `a stale check retry cannot undo an accepted answer`() =
        runTest {
            twoSteps(null)
            api.failures["answerLessonCheck"] = IOException("down")
            val c = loaded { answer(0, 0) }
            val staleKey =
                c.state.value.items
                    .filterIsInstance<ChatItem.ConnectionLost>()
                    .single()
                    .key
            api.failures.clear()
            c.answer(0, 1)
            advanceUntilIdle()
            val bodies = api.bodies.size
            assertTrue(
                c.state.value.items
                    .none { it is ChatItem.ConnectionLost },
            )
            c.retry(staleKey)
            advanceUntilIdle()
            assertEquals(bodies, api.bodies.size)
            assertEquals(
                1,
                c.state.value.items
                    .filterIsInstance<ChatItem.Check>()
                    .single()
                    .answered,
            )
        }

    @Test
    fun `send is refused while the budget message is shown`() =
        runTest {
            twoSteps(null)
            api.failures["postMentorMessage"] = httpError(409, BUDGET_BODY)
            val c = loaded { send("A?", false) }
            assertEquals("Monthly AI budget reached", c.state.value.budgetMessage)
            c.send("B?", false)
            c.explainAgain()
            advanceUntilIdle()
            assertTrue(postedModes().isEmpty())
        }
}
