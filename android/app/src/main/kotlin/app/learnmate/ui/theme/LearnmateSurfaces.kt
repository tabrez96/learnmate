package app.learnmate.ui.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.runtime.Immutable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.dropShadow
import androidx.compose.ui.draw.innerShadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.shadow.Shadow
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp

@Immutable
data class LearnmateSurfaces(
    val cardBorder: Color, // hairline, 1.dp
    val cardShadows: List<Shadow>, // drawn in order, behind the card
    val cardHighlight: Shadow?, // dark only: 1 px inner top highlight
    val glow: Shadow, // under gradient actions
    val selectedBorder: Color, // 2.dp
    val selectedHalo: Color, // 4.dp ring outside the border
    val pageGlowBlue: Color, // already at its alpha
    val pageGlowViolet: Color,
)

private val Violet = Color(0xFF7B4FE0)
private val Glow =
    Shadow(radius = 24.dp, color = Color(0xFF6A4BD8).copy(alpha = 0.55f), spread = (-8).dp, offset = DpOffset(0.dp, 8.dp))

val LightSurfaces =
    LearnmateSurfaces(
        cardBorder = LightColors.ink.copy(alpha = 0.06f),
        cardShadows =
            listOf(
                Shadow(24.dp, LightColors.ink.copy(alpha = 0.10f), spread = (-6).dp, offset = DpOffset(0.dp, 8.dp)),
                Shadow(48.dp, LightColors.blue.copy(alpha = 0.18f), spread = (-24).dp, offset = DpOffset(0.dp, 24.dp)),
            ),
        cardHighlight = null,
        glow = Glow,
        selectedBorder = LightColors.blue,
        selectedHalo = LightColors.blue.copy(alpha = 0.14f),
        pageGlowBlue = LightColors.blue.copy(alpha = 0.10f),
        pageGlowViolet = Violet.copy(alpha = 0.10f),
    )

val DarkSurfaces =
    LearnmateSurfaces(
        cardBorder = Color.White.copy(alpha = 0.07f),
        cardShadows =
            listOf(
                Shadow(32.dp, Color.Black.copy(alpha = 0.45f), spread = (-8).dp, offset = DpOffset(0.dp, 16.dp)),
            ),
        cardHighlight = Shadow(radius = 0.dp, color = Color.White.copy(alpha = 0.06f), offset = DpOffset(0.dp, 1.dp)),
        glow = Glow,
        selectedBorder = DarkColors.blue,
        selectedHalo = DarkColors.blue.copy(alpha = 0.14f),
        pageGlowBlue = DarkColors.blue.copy(alpha = 0.24f),
        pageGlowViolet = Violet.copy(alpha = 0.24f),
    )

/** A floating card: layered shadow, fill, dark-mode top highlight, hairline border. */
fun Modifier.cardSurface(
    surfaces: LearnmateSurfaces,
    color: Color,
    shape: Shape = LearnmateShapes.card,
): Modifier =
    surfaces.cardShadows
        .fold(this) { m, s -> m.dropShadow(shape, s) }
        .background(color, shape)
        .let { m -> surfaces.cardHighlight?.let { m.innerShadow(shape, it) } ?: m }
        .border(1.dp, surfaces.cardBorder, shape)

/** The violet glow under gradient buttons, the current step dot and student bubbles. Put it before the gradient background. */
fun Modifier.gradientGlow(
    surfaces: LearnmateSurfaces,
    shape: Shape,
): Modifier = dropShadow(shape, surfaces.glow)

/** Selected rows and options: 2 dp Blue border with a 4 dp Blue halo outside it. */
fun Modifier.selectedHalo(
    surfaces: LearnmateSurfaces,
    shape: Shape,
): Modifier =
    dropShadow(shape, Shadow(radius = 0.dp, color = surfaces.selectedHalo, spread = 4.dp))
        .border(2.dp, surfaces.selectedBorder, shape)

/** Paper with a soft Blue glow from the top-left corner and a violet one from the top-right. */
fun Modifier.pageBackground(
    paper: Color,
    surfaces: LearnmateSurfaces,
): Modifier =
    drawBehind {
        drawRect(paper)
        val radius = size.width * 0.6f
        drawRect(Brush.radialGradient(listOf(surfaces.pageGlowBlue, Color.Transparent), center = Offset.Zero, radius = radius))
        drawRect(
            Brush.radialGradient(listOf(surfaces.pageGlowViolet, Color.Transparent), center = Offset(size.width, 0f), radius = radius),
        )
    }
