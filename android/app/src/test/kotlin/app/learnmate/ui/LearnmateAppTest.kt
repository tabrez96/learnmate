package app.learnmate.ui

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.StateRestorationTester
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.navigation.NavGraph
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import app.learnmate.ui.navigation.EndSession
import app.learnmate.ui.navigation.HandOver
import app.learnmate.ui.navigation.Mentor
import app.learnmate.ui.navigation.ParentGraph
import app.learnmate.ui.navigation.ParentHome
import app.learnmate.ui.navigation.SessionGraph
import app.learnmate.ui.navigation.SessionHome
import app.learnmate.ui.navigation.SessionLocked
import app.learnmate.ui.navigation.Settings
import app.learnmate.ui.navigation.StartGraph
import app.learnmate.ui.navigation.Test
import app.learnmate.ui.navigation.TestResult
import app.learnmate.ui.navigation.TodaysMaterial
import app.learnmate.ui.theme.LearnmateTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Rule
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class LearnmateAppTest {
    @get:Rule
    val compose = createAndroidComposeRule<ComponentActivity>()

    private lateinit var nav: NavHostController

    private fun launch(start: StartGraph) {
        compose.setContent {
            nav = rememberNavController()
            LearnmateTheme { LearnmateApp(start, nav) }
        }
    }

    private fun pressBack() {
        compose.runOnUiThread { compose.activity.onBackPressedDispatcher.onBackPressed() }
        compose.waitForIdle()
    }

    @org.junit.Test
    fun opensParentGraphWithoutSession() {
        launch(StartGraph.Parent)
        compose.onNodeWithText("S01 Parent home").assertIsDisplayed()
    }

    @org.junit.Test
    fun opensSessionGraphWithSession() {
        launch(StartGraph.Session)
        compose.onNodeWithText("S04 Session home").assertIsDisplayed()
    }

    @org.junit.Test
    fun backDoesNothingInSession() {
        launch(StartGraph.Session)
        pressBack()
        compose.onNodeWithText("S04 Session home").assertIsDisplayed()
        assertFalse(compose.activity.isFinishing)
    }

    @org.junit.Test
    fun backDoesNothingDeeperInSession() {
        launch(StartGraph.Session)
        compose.runOnUiThread { nav.navigate(Mentor) }
        compose.waitForIdle()
        pressBack()
        compose.onNodeWithText("S05 Mentor").assertIsDisplayed()
    }

    private fun restoreWith(
        first: StartGraph,
        second: StartGraph,
    ) {
        val tester = StateRestorationTester(compose)
        // Plain var, not state: changing it must not recompose (and save) the second graph before the restore.
        var start = first
        tester.setContent { LearnmateTheme { LearnmateApp(start) } }
        compose.waitForIdle()
        start = second
        tester.emulateSavedInstanceStateRestore()
        compose.waitForIdle()
    }

    @org.junit.Test
    fun savedSessionStackDoesNotOverrideParentStart() {
        restoreWith(StartGraph.Session, StartGraph.Parent)
        compose.onNodeWithText("S01 Parent home").assertIsDisplayed()
    }

    @org.junit.Test
    fun savedParentStackDoesNotOverrideSessionStart() {
        restoreWith(StartGraph.Parent, StartGraph.Session)
        compose.onNodeWithText("S04 Session home").assertIsDisplayed()
    }

    @org.junit.Test
    fun graphsHoldTheirScreens() {
        launch(StartGraph.Parent)
        val session = nav.graph.findNode<SessionGraph>() as NavGraph
        val parent = nav.graph.findNode<ParentGraph>() as NavGraph
        assertEquals(
            setOf(SessionHome, Mentor, Test, TestResult, EndSession, SessionLocked).map { it::class.qualifiedName }.toSet(),
            session.map { it.route }.toSet(),
        )
        assertEquals(
            setOf(ParentHome, TodaysMaterial, HandOver, Settings).map { it::class.qualifiedName }.toSet(),
            parent.map { it.route }.toSet(),
        )
    }
}
