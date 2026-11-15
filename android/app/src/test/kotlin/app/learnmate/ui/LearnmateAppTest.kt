package app.learnmate.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class LearnmateAppTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun showsAppName() {
        compose.setContent { LearnmateApp() }
        compose.onNodeWithText("Learnmate").assertIsDisplayed()
    }
}
