package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateColors
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

enum class AlertTone { Error, Info, Warning, Ok }

/** Background to text colour. */
fun AlertTone.colors(c: LearnmateColors): Pair<Color, Color> =
    when (this) {
        AlertTone.Error -> c.redTint to c.redText
        AlertTone.Info -> c.blueTint to c.blueText
        AlertTone.Warning -> c.amberTint to c.amberText
        AlertTone.Ok -> c.greenTint to c.greenText
    }

/**
 * Inline message. Compose has no alert or status role, so errors use an assertive live region (role alert)
 * and the other tones a polite one (role status).
 */
@Composable
fun LearnmateAlert(
    text: String,
    tone: AlertTone,
    modifier: Modifier = Modifier,
    title: String? = null,
) {
    val (bg, fg) = tone.colors(LearnmateTheme.colors)
    val mode = if (tone == AlertTone.Error) LiveRegionMode.Assertive else LiveRegionMode.Polite
    Row(
        modifier
            .fillMaxWidth()
            .background(bg, LearnmateShapes.button)
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .semantics(mergeDescendants = true) { liveRegion = mode },
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            Modifier.size(20.dp).background(fg.copy(alpha = 0.16f), CircleShape).clearAndSetSemantics {},
            contentAlignment = Alignment.Center,
        ) {
            when (tone) {
                AlertTone.Ok -> CheckGlyph(fg)
                AlertTone.Info -> Text("i", color = fg, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
                else -> Text("!", color = fg, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
            }
        }
        Column {
            if (title != null) {
                Text(title, color = fg, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
            }
            Text(text, color = fg, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

/** One-line Telegram notice with a paper-plane mark. Polite live region. */
@Composable
fun TelegramLine(
    text: String,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    Row(
        modifier
            .fillMaxWidth()
            .background(colors.telegramTint, LearnmateShapes.button)
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite },
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        PlaneGlyph(colors.telegramText, Modifier.clearAndSetSemantics {})
        Text(text, color = colors.telegramText, style = MaterialTheme.typography.bodyMedium)
    }
}
