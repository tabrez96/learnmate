package app.learnmate

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import app.learnmate.ui.LearnmateApp
import app.learnmate.ui.mentor.MentorRoute
import app.learnmate.ui.navigation.StartGraph
import app.learnmate.ui.navigation.startGraphFor
import app.learnmate.ui.theme.LearnmateTheme
import kotlinx.coroutines.flow.first

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as LearnmateApplication).container
        setContent {
            // null until DataStore has been read, so a stored choice never flashes the wrong mode
            val appearance by container.appearanceRepository.appearance.collectAsState(initial = null)
            // null until Room has been read, so the parent graph never flashes before a running session
            val startGraph by produceState<StartGraph?>(initialValue = null) {
                value = startGraphFor(container.sessionRepository.current.first())
            }
            val mode = appearance
            val start = startGraph
            if (mode != null && start != null) {
                LearnmateTheme(darkTheme = mode.isDark(isSystemInDarkTheme())) {
                    LearnmateApp(start, mentor = {
                        back,
                        test,
                        ->
                        MentorRoute(container, back, test)
                    })
                }
            }
        }
    }
}
