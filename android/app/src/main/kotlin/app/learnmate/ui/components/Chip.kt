package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateColors
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

enum class ChipTone { Blue, Ok, Warn, Bad, Missed, OnHero }

/** Background to text colour. Missed is grey: Line fill with Ink soft text. */
fun ChipTone.colors(c: LearnmateColors): Pair<Color, Color> =
    when (this) {
        ChipTone.Blue -> c.blueTint to c.blueText
        ChipTone.Ok -> c.greenTint to c.greenText
        ChipTone.Warn -> c.amberTint to c.amberText
        ChipTone.Bad -> c.redTint to c.redText
        ChipTone.Missed -> c.line to c.inkSoft
        ChipTone.OnHero -> Color.White.copy(alpha = 0.2f) to Color.White
    }

@Composable
fun LearnmateChip(
    text: String,
    tone: ChipTone,
    modifier: Modifier = Modifier,
) {
    val (bg, fg) = tone.colors(LearnmateTheme.colors)
    val outline =
        if (tone == ChipTone.OnHero) Modifier.border(1.dp, Color.White.copy(alpha = 0.35f), LearnmateShapes.pill) else Modifier
    Text(
        text,
        color = fg,
        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
        modifier = modifier.background(bg, LearnmateShapes.pill).then(outline).padding(horizontal = 12.dp, vertical = 5.dp),
    )
}
