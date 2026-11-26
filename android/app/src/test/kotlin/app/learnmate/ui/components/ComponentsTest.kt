package app.learnmate.ui.components

import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.input.InputMode
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalInputModeManager
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsFocused
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.getBoundsInRoot
import androidx.compose.ui.test.hasProgressBarRangeInfo
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.learnmate.domain.StepState
import app.learnmate.ui.theme.LearnmateTheme
import org.junit.Assert.assertEquals
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
class ComponentsTest {
    @get:Rule val compose = createComposeRule()

    private fun show(content: @androidx.compose.runtime.Composable () -> Unit) =
        compose.setContent { LearnmateTheme(darkTheme = false, compact = false) { content() } }

    @Test
    fun themeSwitch_isSwitchWithCheckedState() {
        var dark by mutableStateOf(false)
        show { ThemeSwitch(dark, { dark = it }) }
        val node = compose.onNodeWithContentDescription("Dark mode")
        node.assert(SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.Switch))
        node.assertIsOff()
        node.performClick()
        node.assertIsOn()
    }

    @Test
    fun primaryAndSecondaryButtons_areAtLeast52dpHigh() {
        show {
            PrimaryButton("Primary", {})
            SecondaryButton("Secondary", {})
            HeroButton("Hero", {})
        }
        listOf("Primary", "Secondary", "Hero").forEach { compose.onNodeWithText(it).assertHeightIsAtLeast(52.dp) }
    }

    @Test
    fun ghostButton_isAtLeast44dpHigh() {
        show { GhostButton("Settings", {}) }
        compose.onNodeWithText("Settings").assertHeightIsAtLeast(44.dp)
    }

    @Test
    fun themeSwitch_isAtLeast44dpHigh() {
        show { ThemeSwitch(false, {}) }
        compose.onNodeWithContentDescription("Dark mode").assertHeightIsAtLeast(44.dp)
    }

    @Test
    fun button_hasButtonRoleAndClicks() {
        var clicks by mutableIntStateOf(0)
        show { PrimaryButton("Continue the lesson", { clicks++ }) }
        val node = compose.onNodeWithText("Continue the lesson")
        node.assert(SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.Button))
        node.performClick()
        assertEquals(1, clicks)
    }

    @Test
    fun disabledButton_doesNotClick() {
        var clicks by mutableIntStateOf(0)
        show { PrimaryButton("Finish setup", { clicks++ }, enabled = false) }
        val node = compose.onNodeWithText("Finish setup")
        node.assertIsNotEnabled()
        node.performClick()
        assertEquals(0, clicks)
    }

    /** Buttons are only focusable in keyboard input mode, as when a keyboard's Tab key is used. */
    @Test
    fun button_takesKeyboardFocus() {
        val requester = FocusRequester()
        show {
            LocalInputModeManager.current.requestInputMode(InputMode.Keyboard)
            PrimaryButton("Continue the lesson", {}, Modifier.focusRequester(requester))
        }
        compose.runOnIdle { requester.requestFocus() }
        compose.onNodeWithText("Continue the lesson").assertIsFocused()
    }

    @Test
    fun progressBar_exposesRange() {
        var progress by mutableStateOf(0.5f)
        show { LearnmateProgressBar(progress) }
        compose.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo(0.5f, 0f..1f))).assertExists()
        progress = 1.5f
        compose.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo(1f, 0f..1f))).assertExists()
    }

    @Test
    fun progressBar_mapsNaNToZero() {
        show { LearnmateProgressBar(Float.NaN) }
        compose.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo(0f, 0f..1f))).assertExists()
    }

    @Test
    @Config(qualifiers = "w360dp-h640dp")
    fun topBar_keepsActionsVisibleOnNarrowLargeFont() {
        compose.setContent {
            LearnmateTheme(darkTheme = false, compact = true) {
                CompositionLocalProvider(LocalDensity provides Density(LocalDensity.current.density, fontScale = 1.3f)) {
                    LearnmateTopBar {
                        ThemeSwitch(false, {})
                        GhostButton("Settings", {})
                    }
                }
            }
        }
        compose.onNodeWithText("Settings").assertIsDisplayed()
        val right = compose.onNodeWithText("Settings").getBoundsInRoot().right
        assertTrue(right <= compose.onRoot().getBoundsInRoot().right)
    }

    @Test
    fun stepRow_announcesState() {
        show {
            StepRow(1, "Warm-up quiz", "Five quick questions", StepState.Done)
            StepRow(2, "Lesson with your mentor", "Learn today's chapter", StepState.Current)
        }
        compose.onNodeWithText("Lesson with your mentor").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Current step"),
        )
        compose.onNodeWithText("Warm-up quiz").assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Done"))
    }

    @Test
    fun sessionPill_showsElapsedMinutes() {
        show { SessionPill(24) }
        compose.onNodeWithText("Session on · 24 min").assertIsDisplayed()
    }

    @Test
    fun topBar_showsWordmark() {
        show { LearnmateTopBar {} }
        compose.onNodeWithText("Learnmate").assertIsDisplayed()
    }
}
