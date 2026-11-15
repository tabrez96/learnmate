package app.learnmate.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun LearnmateApp() {
    MaterialTheme { Surface(modifier = Modifier.fillMaxSize()) { Text("Learnmate") } }
}
