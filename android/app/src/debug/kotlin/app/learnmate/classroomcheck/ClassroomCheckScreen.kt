package app.learnmate.classroomcheck

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp

data class ClassroomCheckState(
    val clientId: String,
    val busy: Boolean = false,
    val lines: List<String> = emptyList(),
)

@Composable
fun ClassroomCheckScreen(
    state: ClassroomCheckState,
    onStart: () -> Unit,
) {
    MaterialTheme {
        Surface {
            Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState())) {
                Text("Classroom check (debug)", style = MaterialTheme.typography.titleLarge)
                Text(
                    if (state.clientId.isBlank()) {
                        "OAuth client id not set: add google.androidClientId to android/local.properties"
                    } else {
                        "OAuth client id: ${state.clientId}"
                    },
                )
                Button(onClick = onStart, enabled = !state.busy) { Text("Sign in and check") }
                if (state.busy) CircularProgressIndicator()
                SelectionContainer {
                    Column { state.lines.forEach { Text(it, fontFamily = FontFamily.Monospace) } }
                }
            }
        }
    }
}
