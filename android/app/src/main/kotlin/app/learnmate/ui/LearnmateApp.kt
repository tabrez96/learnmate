package app.learnmate.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import androidx.compose.ui.Modifier
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.navigation
import androidx.navigation.compose.rememberNavController
import app.learnmate.ui.navigation.EndSession
import app.learnmate.ui.navigation.HandOver
import app.learnmate.ui.navigation.Mentor
import app.learnmate.ui.navigation.ParentGraph
import app.learnmate.ui.navigation.ParentHome
import app.learnmate.ui.navigation.PlaceholderScreen
import app.learnmate.ui.navigation.SessionGraph
import app.learnmate.ui.navigation.SessionHome
import app.learnmate.ui.navigation.SessionLocked
import app.learnmate.ui.navigation.Settings
import app.learnmate.ui.navigation.StartGraph
import app.learnmate.ui.navigation.Test
import app.learnmate.ui.navigation.TestResult
import app.learnmate.ui.navigation.TodaysMaterial
import app.learnmate.ui.theme.LearnmateTheme

@Composable
fun LearnmateApp(
    startGraph: StartGraph,
    // Keyed by startGraph so a saved back stack only restores under the start graph it was saved with.
    navController: NavHostController = key(startGraph) { rememberNavController() },
    mentor: @Composable (onBack: () -> Unit, onReadyForTest: () -> Unit) -> Unit = { _, _ -> PlaceholderScreen("S05", "Mentor") },
) {
    Surface(modifier = Modifier.fillMaxSize(), color = LearnmateTheme.colors.paper) {
        NavHost(navController, startDestination = if (startGraph == StartGraph.Session) SessionGraph else ParentGraph) {
            navigation<ParentGraph>(startDestination = ParentHome) {
                composable<ParentHome> { PlaceholderScreen("S01", "Parent home") }
                composable<TodaysMaterial> { PlaceholderScreen("S02", "Today's material") }
                composable<HandOver> { PlaceholderScreen("S03", "Hand over") }
                composable<Settings> { PlaceholderScreen("S09", "Settings") }
            }
            navigation<SessionGraph>(startDestination = SessionHome) {
                sessionScreen<SessionHome> { PlaceholderScreen("S04", "Session home") }
                sessionScreen<Mentor> { mentor({ navController.popBackStack() }, { navController.navigate(Test) }) }
                sessionScreen<Test> { PlaceholderScreen("S06", "Test") }
                sessionScreen<TestResult> { PlaceholderScreen("S07", "Test result") }
                sessionScreen<EndSession> { PlaceholderScreen("S08", "End session") }
                sessionScreen<SessionLocked> { PlaceholderScreen("S11", "Session locked") }
            }
        }
    }
}

/** A session screen: back is swallowed, so the child can't leave the session or the app. */
private inline fun <reified T : Any> NavGraphBuilder.sessionScreen(noinline content: @Composable () -> Unit) {
    composable<T> {
        BackHandler(enabled = true) {}
        content()
    }
}
