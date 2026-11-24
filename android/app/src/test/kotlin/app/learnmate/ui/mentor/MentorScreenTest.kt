package app.learnmate.ui.mentor

import androidx.compose.ui.input.key.Key
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performKeyInput
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.pressKey
import app.learnmate.session.mentor.BOOKS_ONLY_FOOTER
import app.learnmate.session.mentor.ChatItem
import app.learnmate.session.mentor.MentorUiState
import app.learnmate.ui.theme.LearnmateTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@OptIn(ExperimentalTestApi::class)
@RunWith(RobolectricTestRunner::class)
@Config(qualifiers = "w1280dp-h800dp-mdpi")
class MentorScreenTest {
    @get:Rule val compose = createComposeRule()

    private val sent = mutableListOf<Pair<String, Boolean>>()
    private val answers = mutableListOf<Pair<Int, Int>>()
    private val outsideChecks = mutableListOf<String>()

    private fun show(state: MentorUiState) {
        compose.setContent {
            LearnmateTheme(darkTheme = false, compact = false) {
                MentorScreen(
                    state = state,
                    dark = false,
                    elapsedMinutes = 3,
                    onDarkChange = {},
                    onBack = {},
                    onAnswer = { step, option -> answers += step to option },
                    onNextStep = {},
                    onExplainAgain = {},
                    onSend = { text, outside -> sent += text to outside },
                    onCheckOutside = { outsideChecks += it },
                    onRetry = {},
                    onReadyForTest = {},
                )
            }
        }
    }

    private fun state(
        outsideAllowed: Boolean = true,
        items: List<ChatItem> = emptyList(),
        budgetMessage: String? = null,
    ) = MentorUiState(
        loading = false,
        ready = true,
        topic = "Photosynthesis",
        stepTitles = listOf("What plants need", "Chlorophyll"),
        stepIndex = 1,
        items = items,
        outsideAllowed = outsideAllowed,
        budgetMessage = budgetMessage,
    )

    private fun radio(title: String) =
        compose.onNode(
            SemanticsMatcher("radio option $title") {
                it.config.getOrNull(SemanticsProperties.Role) == Role.RadioButton
            } and hasText(title, substring = true),
        )

    @Test
    fun `send button sends in books mode`() {
        show(state())
        compose.onNodeWithTag("composer").performTextInput("Why is it green?")
        compose.onNodeWithTag("send").performClick()
        assertEquals(listOf("Why is it green?" to false), sent)
        compose.onNodeWithTag("composer").assertTextEquals("Ask your mentor…", "")
    }

    @Test
    fun `enter key sends in books mode`() {
        show(state())
        compose.onNodeWithTag("composer").performTextInput("Why?")
        compose.onNodeWithTag("composer").performKeyInput { pressKey(Key.Enter) }
        assertEquals(listOf("Why?" to false), sent)
    }

    @Test
    fun `blank text is not sent`() {
        show(state())
        compose.onNodeWithTag("composer").performKeyInput { pressKey(Key.Enter) }
        compose.onNodeWithTag("send").assertIsNotEnabled()
        assertEquals(emptyList<Pair<String, Boolean>>(), sent)
    }

    @Test
    fun `menu item sends outside`() {
        show(state())
        compose.onNodeWithTag("composer").performTextInput("Who wrote it?")
        compose.onNodeWithTag("sendArrow").performClick()
        compose.onNodeWithText("Send and check outside the books").performClick()
        assertEquals(listOf("Who wrote it?" to true), sent)
    }

    @Test
    fun `arrow is hidden when outside is off`() {
        val question = "Why?"
        show(state(outsideAllowed = false, items = listOf(ChatItem.Mentor("a", "Not covered.", null, checkOutsideFor = question))))
        compose.onAllNodesWithTag("sendArrow").assertCountEquals(0)
        compose.onAllNodesWithText("Check outside the books").assertCountEquals(0)
        compose.onNodeWithText(BOOKS_ONLY_FOOTER).assertIsDisplayed()
    }

    @Test
    fun `not covered reply offers the outside check`() {
        show(state(items = listOf(ChatItem.Mentor("a", "Not covered.", null, checkOutsideFor = "Why?"))))
        compose.onNodeWithText("Check outside the books").performClick()
        assertEquals(listOf("Why?"), outsideChecks)
    }

    @Test
    fun `arrow is a menu button`() {
        show(state())
        compose.onNodeWithTag("composer").performTextInput("x")
        val arrow = compose.onNodeWithTag("sendArrow")
        arrow.assert(SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.DropdownList))
        arrow.assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Collapsed"))
        arrow.performClick()
        arrow.assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Expanded"))
        radio("Answer only from your books").assertIsSelected()
        radio("Looks it up on trusted sites").assertExists()
    }

    @Test
    fun `escape closes the menu`() {
        show(state())
        compose.onNodeWithTag("composer").performTextInput("x")
        compose.onNodeWithTag("sendArrow").performClick()
        compose.onNodeWithTag("sendMenu").assertExists()
        compose.onNodeWithTag("sendMenu").performKeyInput { pressKey(Key.Escape) }
        compose.onAllNodesWithTag("sendMenu").assertCountEquals(0)
    }

    @Test
    fun `budget message is shown as a warning alert`() {
        show(state(budgetMessage = "Monthly AI budget reached"))
        compose.onNodeWithText("Monthly AI budget reached").assertIsDisplayed()
        compose.onNodeWithText("Lessons are paused").assertIsDisplayed()
        compose.onNodeWithTag("send").assertIsNotEnabled()
        compose.onNodeWithTag("composer").assertIsNotEnabled()
    }

    @Test
    fun `chat is a polite live region`() {
        show(state())
        compose.onNodeWithTag("chat").assert(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite))
    }

    @Test
    fun `check option calls onAnswer`() {
        show(state(items = listOf(ChatItem.Check("c", 1, "What colour?", listOf("Green", "Red")))))
        compose.onNodeWithText("Quick check: What colour?").assertIsDisplayed()
        compose.onNodeWithText("Red").performClick()
        assertEquals(listOf(1 to 1), answers)
    }

    @Test
    fun `answered check hides its options`() {
        show(state(items = listOf(ChatItem.Check("c", 1, "What colour?", listOf("Green", "Red"), answered = 0))))
        compose.onAllNodesWithText("Red").assertCountEquals(0)
    }

    @Test
    fun `placeholder replaces a visual and outside bubble has its chip and source`() {
        show(
            state(
                items =
                    listOf(
                        ChatItem.Mentor("a", "Answer", "From: Science notes, p.32", hasVisual = true),
                        ChatItem.Outside("b", "Outside answer", "Source: britannica.com"),
                    ),
            ),
        )
        compose.onNodeWithText("I couldn't show the picture, but the answer above still stands.").assertIsDisplayed()
        compose.onNodeWithText("Checked outside your books").assertIsDisplayed()
        compose.onNodeWithText("Source: britannica.com").assertIsDisplayed()
    }

    @Test
    fun `connection lost offers try again and the last step offers the test`() {
        show(state(items = listOf(ChatItem.ConnectionLost("a"), ChatItem.ReadyForTest("b"))))
        compose.onNodeWithText("I lost my connection. Your progress is saved.").assertIsDisplayed()
        compose.onNodeWithText("Try again").assertIsDisplayed()
        compose.onNodeWithText("Ready for your test?").assertIsDisplayed()
        compose.onNodeWithText("Start the test").assertIsDisplayed()
    }
}
