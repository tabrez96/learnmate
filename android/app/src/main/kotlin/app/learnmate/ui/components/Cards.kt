package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.cardSurface
import app.learnmate.ui.theme.gradientGlow

private val HeroRose = Color(0xFFFF9CC8)

@Composable
fun LearnmateCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier.cardSurface(LearnmateTheme.surfaces, LearnmateTheme.colors.card).padding(LearnmateSpacing.cardPadding),
        verticalArrangement = Arrangement.spacedBy(LearnmateSpacing.blockGap),
        content = content,
    )
}

@Composable
fun GradientHeroCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .gradientGlow(LearnmateTheme.surfaces, LearnmateShapes.card)
            .clip(LearnmateShapes.card)
            .background(LearnmateTheme.gradients.brand)
            .drawBehind { heroCircles() }
            .padding(28.dp),
        verticalArrangement = Arrangement.spacedBy(LearnmateSpacing.blockGap),
    ) {
        CompositionLocalProvider(LocalContentColor provides Color.White) { content() }
    }
}

private fun DrawScope.heroCircles() {
    softCircle(Color.White.copy(alpha = 0.18f), Offset(size.width * 0.88f, size.height * 0.1f), size.height * 0.7f)
    softCircle(HeroRose.copy(alpha = 0.22f), Offset(size.width * 0.55f, size.height * 1.05f), size.height * 0.6f)
}

private fun DrawScope.softCircle(
    color: Color,
    at: Offset,
    radius: Float,
) = drawCircle(Brush.radialGradient(listOf(color, Color.Transparent), center = at, radius = radius), radius = radius, center = at)

@Composable
fun StatTile(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
    icon: String? = null,
) {
    val colors = LearnmateTheme.colors
    Column(
        modifier
            .cardSurface(LearnmateTheme.surfaces, colors.card, LearnmateShapes.tile)
            .padding(18.dp)
            .semantics(mergeDescendants = true) {},
    ) {
        Row(verticalAlignment = Alignment.Bottom) {
            if (icon != null) {
                Text(icon, fontSize = 16.sp, modifier = Modifier.clearAndSetSemantics {}.padding(end = 6.dp))
            }
            Text(value, color = colors.ink, style = MaterialTheme.typography.headlineLarge.copy(fontSize = 28.sp, lineHeight = 34.sp))
        }
        Text(label, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
    }
}
