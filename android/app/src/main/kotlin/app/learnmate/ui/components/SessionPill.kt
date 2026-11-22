package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

fun sessionPillLabel(elapsedMinutes: Int): String = "Session on · $elapsedMinutes min"

@Composable
fun SessionPill(
    elapsedMinutes: Int,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    Row(
        modifier
            .height(36.dp)
            .background(colors.greenTint, LearnmateShapes.pill)
            .border(1.dp, colors.green.copy(alpha = 0.3f), LearnmateShapes.pill)
            .padding(start = 10.dp, end = 14.dp)
            .semantics(mergeDescendants = true) {},
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            Modifier.size(16.dp).clearAndSetSemantics {}.background(colors.green.copy(alpha = 0.25f), CircleShape),
            contentAlignment = Alignment.Center,
        ) { Box(Modifier.size(8.dp).background(colors.green, CircleShape)) }
        LockGlyph(colors.greenText, modifier = Modifier.clearAndSetSemantics {})
        Text(
            sessionPillLabel(elapsedMinutes),
            color = colors.greenText,
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
        )
    }
}
