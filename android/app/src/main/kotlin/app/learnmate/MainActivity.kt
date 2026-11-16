package app.learnmate

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import app.learnmate.ui.LearnmateApp
import app.learnmate.ui.theme.LearnmateTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val appearanceRepository = (application as LearnmateApplication).container.appearanceRepository
        setContent {
            // null until DataStore has been read, so a stored choice never flashes the wrong mode
            val appearance by appearanceRepository.appearance.collectAsState(initial = null)
            appearance?.let {
                LearnmateTheme(darkTheme = it.isDark(isSystemInDarkTheme())) { LearnmateApp() }
            }
        }
    }
}
