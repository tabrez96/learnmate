package app.learnmate.slice

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import app.learnmate.BuildConfig

data class SliceState(
    val subject: String = "",
    val fileName: String? = null,
    val busy: Boolean = false,
    val status: List<String> = emptyList(),
    val log: String = "",
    val canResume: Boolean = false,
)

@Composable
fun SliceScreen(
    state: SliceState,
    onSubjectChange: (String) -> Unit,
    onPickFile: () -> Unit,
    onRun: () -> Unit,
    onResume: () -> Unit,
    onEndCurrent: () -> Unit,
    onRefreshCost: () -> Unit,
) {
    Surface {
        Column(
            Modifier.padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Slice run (debug)", style = MaterialTheme.typography.titleLarge)
            Text("Server: ${BuildConfig.SERVER_URL}")
            OutlinedTextField(
                value = state.subject,
                onValueChange = onSubjectChange,
                label = { Text("Subject name") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onPickFile, enabled = !state.busy) { Text("Pick file") }
                Text(state.fileName ?: "No file picked")
            }
            Button(
                onClick = onRun,
                enabled = !state.busy && state.subject.isNotBlank() && state.fileName != null,
            ) { Text("Upload and start") }
            if (state.canResume) OutlinedButton(onClick = onResume, enabled = !state.busy) { Text("Resume in S05") }
            OutlinedButton(onClick = onEndCurrent, enabled = !state.busy) { Text("End current session") }
            OutlinedButton(onClick = onRefreshCost, enabled = !state.busy) { Text("Record AI cost") }
            if (state.busy) CircularProgressIndicator()
            state.status.forEach { Text(it, fontFamily = FontFamily.Monospace) }
            SelectionContainer { Text(state.log, fontFamily = FontFamily.Monospace) }
        }
    }
}
