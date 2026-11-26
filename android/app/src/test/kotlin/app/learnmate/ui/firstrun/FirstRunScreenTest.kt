package app.learnmate.ui.firstrun

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import app.learnmate.ui.theme.LearnmateTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(qualifiers = "w1280dp-h1600dp-mdpi")
class FirstRunScreenTest {
    @get:Rule val compose = createComposeRule()

    private val ready =
        FirstRunUiState(
            loading = false,
            childName = "Omar",
            grade = 7,
            familySaved = true,
            telegramConnected = true,
            telegramHandle = "omars_parent",
            password = SAMPLE_TYPED,
            passwordAgain = SAMPLE_TYPED,
        )

    private fun show(
        state: FirstRunUiState,
        onFinish: () -> Unit = {},
    ) = compose.setContent {
        LearnmateTheme { FirstRunScreen(state, false, {}, {}, {}, {}, {}, {}, {}, onFinish, {}) }
    }

    @Test
    fun finishIsDisabledWithoutTelegram() {
        show(ready.copy(telegramConnected = false))
        compose.onNodeWithText("Finish setup").assertIsNotEnabled()
    }

    @Test
    fun finishIsDisabledWhenPasswordsDiffer() {
        show(ready.copy(passwordAgain = SAMPLE_TYPO))
        compose.onNodeWithText("Finish setup").assertIsNotEnabled()
        compose.onNodeWithText("The two passwords don't match").assertIsDisplayed()
    }

    @Test
    fun finishIsEnabledAndCallsBack() {
        var finished = 0
        show(ready) { finished++ }
        compose.onNodeWithText("Finish setup").assertIsEnabled().performClick()
        assertEquals(1, finished)
    }

    @Test
    fun connectedLineShowsTheHandle() {
        show(ready)
        compose.onNodeWithText("Connected: @omars_parent. Grades, alerts and session PINs arrive here.").assertIsDisplayed()
    }

    @Test
    fun codeStateShowsTheCommand() {
        show(ready.copy(telegramConnected = false, linkCode = "abc123"))
        compose.onNodeWithText("/start abc123").assertIsDisplayed()
        compose.onNodeWithText("Waiting for Telegram…").assertIsDisplayed()
    }

    @Test
    fun shortPasswordShowsItsMessage() {
        show(ready.copy(password = SAMPLE_SHORT, passwordAgain = ""))
        compose.onNodeWithText("Use at least 8 characters").assertIsDisplayed()
    }

    @Test
    fun loadFailureOffersRetry() {
        show(FirstRunUiState(loading = false, loadFailed = true, error = NETWORK_ERROR))
        compose.onNodeWithText("Try again").assertIsDisplayed()
    }
}
