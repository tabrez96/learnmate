package app.learnmate.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

@Immutable
data class LearnmateGradients(
    val brand: Brush,
    val text: Brush,
    val gold: Brush,
)

/** The design's 135deg gradients run from the top-left to the bottom-right corner of whatever they fill. */
fun diagonalGradient(colors: List<Color>): Brush = Brush.linearGradient(colors, start = Offset.Zero, end = Offset.Infinite)

private val Brand = diagonalGradient(listOf(Color(0xFF3949C8), Color(0xFF6A4BD8), Color(0xFF9B4DCB)))
private val Gold = diagonalGradient(listOf(Color(0xFFF2A516), Color(0xFFF57C4B)))

val LightGradients =
    LearnmateGradients(
        brand = Brand,
        text = diagonalGradient(listOf(Color(0xFF3949C8), Color(0xFF7B4FE0), Color(0xFFB94A9E))),
        gold = Gold,
    )

val DarkGradients =
    LearnmateGradients(
        brand = Brand,
        text = diagonalGradient(listOf(Color(0xFF9AA6FF), Color(0xFFC3A2FF), Color(0xFFFF9CC8))),
        gold = Gold,
    )
