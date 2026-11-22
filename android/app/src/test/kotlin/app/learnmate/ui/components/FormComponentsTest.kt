package app.learnmate.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.state.ToggleableState
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotSelected
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.click
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w1000dp-h700dp-mdpi")
class FormComponentsTest {
    @get:Rule val compose = createComposeRule()

    private fun show(content: @Composable () -> Unit) =
        compose.setContent { LearnmateTheme(darkTheme = false, compact = false) { content() } }

    private fun role(r: Role) = SemanticsMatcher.expectValue(SemanticsProperties.Role, r)

    @Test
    fun toggle_isSwitchAndToggles() {
        var on by mutableStateOf(false)
        show { LearnmateToggle("Send grades", on, { on = it }) }
        val node = compose.onNodeWithText("Send grades")
        node.assert(role(Role.Switch))
        node.assertIsOff()
        node.performClick()
        node.assertIsOn()
    }

    @Test
    fun disabledToggle_doesNotChange() {
        var on by mutableStateOf(false)
        show { LearnmateToggle("Send grades", on, { on = it }, enabled = false) }
        compose.onNodeWithText("Send grades").performClick()
        compose.onNodeWithText("Send grades").assertIsOff()
    }

    @Test
    fun subjectTiles_formRadioGroup() {
        var clicked = 0
        show {
            SubjectTileGroup(Modifier.testTag("group")) {
                SubjectTile("📐", "Maths", 4, "82% B", selected = true, onClick = {})
                SubjectTile("🔬", "Science", 0, null, selected = false, onClick = { clicked++ })
            }
        }
        compose.onNodeWithTag("group").assert(SemanticsMatcher.keyIsDefined(SemanticsProperties.SelectableGroup))
        compose.onNodeWithText("Maths").assert(role(Role.RadioButton)).assertIsSelected()
        compose.onNodeWithText("Science").assertIsNotSelected().performClick()
        assertEquals(1, clicked)
    }

    @Test
    fun subjectTile_showsNothingYetWithoutGrade() {
        show { SubjectTile("🔬", "Science", 0, null, selected = false, onClick = {}) }
        compose.onNodeWithText("Nothing yet", substring = true).assertIsDisplayed()
        compose.onNodeWithText("0 materials", substring = true).assertIsDisplayed()
    }

    @Test
    fun libraryRow_isCheckbox() {
        var checked by mutableStateOf(false)
        show { LibraryRow("pdf", "Fractions", "Added 12 Nov", checked, { checked = it }) }
        val node = compose.onNodeWithText("Fractions")
        node.assert(role(Role.Checkbox))
        node.assert(SemanticsMatcher.expectValue(SemanticsProperties.ToggleableState, ToggleableState.Off))
        node.performClick()
        node.assert(SemanticsMatcher.expectValue(SemanticsProperties.ToggleableState, ToggleableState.On))
    }

    @Test
    fun keypadKeys_are88x72() {
        show { PinKeypad({}, {}) }
        for (label in listOf("1", "0", "Delete")) {
            compose.onNodeWithText(label).assertWidthIsEqualTo(88.dp).assertHeightIsEqualTo(72.dp)
        }
    }

    @Test
    fun keypad_emitsDigitsAndDelete() {
        val digits = mutableListOf<Int>()
        var deletes = 0
        show { PinKeypad({ digits += it }, { deletes++ }) }
        compose.onNodeWithText("4").performClick()
        compose.onNodeWithText("7").performClick()
        compose.onNodeWithText("Delete").performClick()
        assertEquals(listOf(4, 7), digits)
        assertEquals(1, deletes)
    }

    @Test
    fun keypad_layoutIs3x4() {
        assertEquals(4, KeypadLayout.size)
        assertTrue(KeypadLayout.all { it.size == 3 })
        val digits = KeypadLayout.flatten().filterIsInstance<KeypadKey.Digit>().map { it.value }
        assertEquals((0..9).toList(), digits.sorted())
    }

    @Test
    fun answerOption_is84High() {
        show { AnswerOption('A', "One half", AnswerState.Default, {}, Modifier.testTag("opt")) }
        compose.onNodeWithTag("opt").assertHeightIsEqualTo(84.dp)
    }

    @Test
    fun rightAndWrongOptions_carryText() {
        show {
            Column {
                AnswerOption('A', "One", AnswerState.Right, {})
                AnswerOption('B', "Two", AnswerState.Wrong, {})
                AnswerOption('C', "Three", AnswerState.Default, {})
            }
        }
        compose.onNodeWithText("Correct!").assertIsDisplayed()
        compose.onNodeWithText("Your answer").assertIsDisplayed()
    }

    @Test
    fun disabledAnswerOption_doesNotClick() {
        var clicked = false
        show { AnswerOption('A', "One half", AnswerState.Right, { clicked = true }, enabled = false) }
        compose.onNodeWithText("One half").performClick()
        assertTrue(!clicked)
        compose.onNodeWithText("Correct!").assertIsDisplayed()
    }

    @Test
    fun alerts_useLiveRegions() {
        show {
            Column {
                LearnmateAlert("Bad PIN", AlertTone.Error)
                LearnmateAlert("Saved", AlertTone.Ok)
                TelegramLine("Grade sent to Telegram")
            }
        }

        fun live(mode: LiveRegionMode) = SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, mode)
        compose.onNodeWithText("Bad PIN").assert(live(LiveRegionMode.Assertive))
        compose.onNodeWithText("Saved").assert(live(LiveRegionMode.Polite))
        compose.onNodeWithText("Grade sent to Telegram").assert(live(LiveRegionMode.Polite))
    }

    @Test
    fun segmentedControl_selectsOption() {
        var picked = -1
        show { SegmentedControl(listOf("Learn and test", "Test only"), 0, { picked = it }) }
        compose.onNodeWithText("Learn and test").assertIsSelected()
        compose.onNodeWithText("Test only").performClick()
        assertEquals(1, picked)
    }

    @Test
    fun sideNav_marksActiveItem() {
        var picked = -1
        show { SideNav(listOf(SideNavItem("Appearance"), SideNavItem("Telegram")), 0, { picked = it }) }
        compose.onNodeWithText("Appearance").assertIsSelected()
        compose.onNodeWithText("Telegram").assertIsNotSelected().performClick()
        assertEquals(1, picked)
    }

    @Test
    fun passwordField_showToggles() {
        var v by mutableStateOf("")
        show { PasswordField(v, { v = it }, "Password") }
        compose.onNodeWithText("Password").performTextInput("abc123")
        val field = compose.onNode(SemanticsMatcher.keyIsDefined(SemanticsProperties.EditableText))
        field.assert(SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString("\u2022".repeat(6))))
        compose.onNodeWithContentDescription("Show password").performClick()
        field.assert(SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString("abc123")))
        compose.onNodeWithContentDescription("Hide password").assertExists()
    }

    @Test
    fun pinDots_describeProgress() {
        show { PinDots(2) }
        compose.onNodeWithContentDescription("2 of 4 digits entered").assertExists()
    }

    @Test
    fun pinDots_announceRejectedPin() {
        show { PinDots(4, error = true) }
        compose.onNodeWithContentDescription("4 of 4 digits entered, PIN not accepted").assertExists()
    }

    @Test
    fun dialogHost_hidesBackgroundAndDismisses() {
        var dismissed = false
        show {
            LearnmateDialogHost(
                title = "Add subject",
                onDismiss = { dismissed = true },
                content = { Text("Behind") },
                dialog = { Text("Body") },
            )
        }
        compose.onNodeWithText("Behind").assertDoesNotExist()
        compose.onNodeWithText("Add subject").assertIsDisplayed()
        compose.onRoot().performTouchInput { click(Offset(5f, 5f)) }
        assertTrue(dismissed)
    }

    @Test
    fun dialogHost_tapInsideCardDoesNotDismiss() {
        var dismissed = false
        show {
            LearnmateDialogHost(
                title = "Add subject",
                onDismiss = { dismissed = true },
                content = { Text("Behind") },
                dialog = { Text("Body") },
            )
        }
        compose.onNodeWithText("Add subject").performClick()
        assertFalse(dismissed)
    }

    @Test
    fun dialogHost_tapInCardPaddingDoesNotDismiss() {
        var dismissed = false
        show {
            LearnmateDialogHost(
                title = "Add subject",
                onDismiss = { dismissed = true },
                content = { Text("Behind") },
                dialog = { Text("Body") },
            )
        }
        // The title sits inside the card's inner padding, so a point just up and left of it is on the card.
        val title = compose.onNodeWithText("Add subject").fetchSemanticsNode().positionInRoot
        compose.onRoot().performTouchInput { click(Offset(title.x - 8f, title.y - 8f)) }
        assertFalse(dismissed)
    }
}
