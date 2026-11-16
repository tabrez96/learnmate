package app.learnmate.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import app.learnmate.ui.theme.LearnmateTheme

@Composable
fun LearnmateApp() {
    Surface(modifier = Modifier.fillMaxSize(), color = LearnmateTheme.colors.paper) {
        Text("Learnmate", color = LearnmateTheme.colors.ink)
    }
}
