package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.gradientGlow
import app.learnmate.ui.theme.selectedHalo

enum class StepState { Done, Current, Upcoming }

internal val StepState.description: String
    get() =
        when (this) {
            StepState.Done -> "Done"
            StepState.Current -> "Current step"
            StepState.Upcoming -> "Up next"
        }

@Composable
fun StepRow(
    number: Int,
    title: String,
    subtitle: String,
    state: StepState,
    modifier: Modifier = Modifier,
    trailing: (@Composable () -> Unit)? = null,
) {
    val colors = LearnmateTheme.colors
    val surfaces = LearnmateTheme.surfaces
    val shape = LearnmateShapes.button
    val outline = if (state == StepState.Current) Modifier.selectedHalo(surfaces, shape) else Modifier.border(1.dp, colors.line, shape)
    Row(
        modifier
            .fillMaxWidth()
            .defaultMinSize(minHeight = 68.dp)
            .then(outline)
            .background(colors.card, shape)
            .padding(horizontal = 14.dp, vertical = 12.dp)
            .semantics(mergeDescendants = true) { stateDescription = state.description },
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        StepDot(number, state)
        Column(Modifier.weight(1f)) {
            Text(title, color = colors.ink, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
        }
        trailing?.invoke()
    }
}

@Composable
private fun StepDot(
    number: Int,
    state: StepState,
) {
    val colors = LearnmateTheme.colors
    val base = Modifier.size(34.dp).clearAndSetSemantics {}
    val numberStyle = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold)
    when (state) {
        StepState.Done ->
            Box(base.background(colors.green, CircleShape), contentAlignment = Alignment.Center) { CheckGlyph(Color.White) }
        StepState.Current ->
            Box(
                base.gradientGlow(LearnmateTheme.surfaces, CircleShape).background(LearnmateTheme.gradients.brand, CircleShape),
                contentAlignment = Alignment.Center,
            ) { Text("$number", color = Color.White, style = numberStyle) }
        StepState.Upcoming ->
            Box(base.background(colors.blueTint, CircleShape), contentAlignment = Alignment.Center) {
                Text("$number", color = colors.blueText, style = numberStyle)
            }
    }
}
