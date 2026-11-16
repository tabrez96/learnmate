package app.learnmate.classroomcheck

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ClassroomCheckScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun showsMissingClientIdHint() {
        compose.setContent { ClassroomCheckScreen(ClassroomCheckState(clientId = ""), onStart = {}) }
        compose.onNodeWithText("google.androidClientId", substring = true).assertIsDisplayed()
    }

    @Test
    fun showsLinesAndDisablesButtonWhileBusy() {
        val state = ClassroomCheckState(clientId = "id", busy = true, lines = listOf("RESULT: OK"))
        compose.setContent { ClassroomCheckScreen(state, onStart = {}) }
        compose.onNodeWithText("RESULT: OK").assertIsDisplayed()
        compose.onNodeWithText("Sign in and check").assertIsNotEnabled()
    }
}
