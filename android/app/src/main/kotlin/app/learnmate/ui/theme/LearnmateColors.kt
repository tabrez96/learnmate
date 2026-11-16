package app.learnmate.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.ui.graphics.Color

@Immutable
data class LearnmateColors(
    val paper: Color,
    val card: Color,
    val line: Color,
    val ink: Color,
    val inkSoft: Color,
    val blue: Color,
    val blueTint: Color,
    val blueText: Color,
    val green: Color,
    val greenTint: Color,
    val greenText: Color,
    val red: Color,
    val redTint: Color,
    val redText: Color,
    val amberTint: Color,
    val amberText: Color,
    val telegramTint: Color,
    val telegramText: Color,
) {
    /** Token names as written in the design's Colours table, in table order. */
    fun tokens(): List<Pair<String, Color>> =
        listOf(
            "Paper" to paper,
            "Card" to card,
            "Line" to line,
            "Ink" to ink,
            "Ink soft" to inkSoft,
            "Blue" to blue,
            "Blue tint" to blueTint,
            "Blue text" to blueText,
            "Green" to green,
            "Green tint" to greenTint,
            "Green text" to greenText,
            "Red" to red,
            "Red tint" to redTint,
            "Red text" to redText,
            "Amber tint" to amberTint,
            "Amber text" to amberText,
            "Telegram tint" to telegramTint,
            "Telegram text" to telegramText,
        )
}

val LightColors =
    LearnmateColors(
        paper = Color(0xFFF7F5EF),
        card = Color(0xFFFFFFFF),
        line = Color(0xFFE7E3D8),
        ink = Color(0xFF1E2640),
        inkSoft = Color(0xFF5B6478),
        blue = Color(0xFF3949C8),
        blueTint = Color(0xFFECEEFB),
        blueText = Color(0xFF2C3AA8),
        green = Color(0xFF1F9D6B),
        greenTint = Color(0xFFE2F4EC),
        greenText = Color(0xFF13704B),
        red = Color(0xFFD64545),
        redTint = Color(0xFFFBE5E5),
        redText = Color(0xFFA92F2F),
        amberTint = Color(0xFFFFF1D6),
        amberText = Color(0xFF8A5A00),
        telegramTint = Color(0xFFE8F4FB),
        telegramText = Color(0xFF14567A),
    )

val DarkColors =
    LearnmateColors(
        paper = Color(0xFF11152A),
        card = Color(0xFF1B2040),
        line = Color(0xFF2E3560),
        ink = Color(0xFFEEF0FA),
        inkSoft = Color(0xFFA7AECB),
        blue = Color(0xFF8E9BFF),
        blueTint = Color(0xFF272F66),
        blueText = Color(0xFFC3C9FF),
        green = Color(0xFF3CC48C),
        greenTint = Color(0xFF16392E),
        greenText = Color(0xFF7FE0B4),
        red = Color(0xFFF06A6A),
        redTint = Color(0xFF45212A),
        redText = Color(0xFFFFA8A8),
        amberTint = Color(0xFF3B3016),
        amberText = Color(0xFFF2C76B),
        telegramTint = Color(0xFF15314A),
        telegramText = Color(0xFF93CDF2),
    )
