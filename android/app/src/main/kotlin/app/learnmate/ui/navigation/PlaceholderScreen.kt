package app.learnmate.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import app.learnmate.ui.theme.LearnmateTheme

/** Temporary screen body until the real screen is built. */
@Composable
fun PlaceholderScreen(
    screenId: String,
    title: String,
) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text("$screenId $title", color = LearnmateTheme.colors.ink, style = MaterialTheme.typography.titleLarge)
    }
}
