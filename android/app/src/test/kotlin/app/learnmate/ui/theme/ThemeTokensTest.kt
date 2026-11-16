package app.learnmate.ui.theme

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Test

class ThemeTokensTest {
    private fun LearnmateColors.hex() = tokens().map { (name, color) -> name to "#%06X".format(color.toArgb() and 0xFFFFFF) }

    private fun gradient(vararg rgb: Long): Brush = Brush.linearGradient(rgb.map { Color(0xFF000000 or it) }, Offset.Zero, Offset.Infinite)

    /** Name, light hex, dark hex: the Colours table of design/ux.md, in table order. */
    private val expected =
        listOf(
            Triple("Paper", "#F7F5EF", "#11152A"),
            Triple("Card", "#FFFFFF", "#1B2040"),
            Triple("Line", "#E7E3D8", "#2E3560"),
            Triple("Ink", "#1E2640", "#EEF0FA"),
            Triple("Ink soft", "#5B6478", "#A7AECB"),
            Triple("Blue", "#3949C8", "#8E9BFF"),
            Triple("Blue tint", "#ECEEFB", "#272F66"),
            Triple("Blue text", "#2C3AA8", "#C3C9FF"),
            Triple("Green", "#1F9D6B", "#3CC48C"),
            Triple("Green tint", "#E2F4EC", "#16392E"),
            Triple("Green text", "#13704B", "#7FE0B4"),
            Triple("Red", "#D64545", "#F06A6A"),
            Triple("Red tint", "#FBE5E5", "#45212A"),
            Triple("Red text", "#A92F2F", "#FFA8A8"),
            Triple("Amber tint", "#FFF1D6", "#3B3016"),
            Triple("Amber text", "#8A5A00", "#F2C76B"),
            Triple("Telegram tint", "#E8F4FB", "#15314A"),
            Triple("Telegram text", "#14567A", "#93CDF2"),
        )

    @Test
    fun tokensMatchDesign() {
        assertEquals(expected.map { it.first to it.second }, LightColors.hex())
        assertEquals(expected.map { it.first to it.third }, DarkColors.hex())
    }

    @Test
    fun colorSchemeMapsTokens() {
        val light = LightColors.toColorScheme(dark = false)
        val dark = DarkColors.toColorScheme(dark = true)
        assertEquals(Color(0xFFF7F5EF), light.background)
        assertEquals(Color(0xFF3949C8), light.primary)
        assertEquals(Color.White, light.onPrimary)
        assertEquals(Color(0xFF11152A), dark.background)
        assertEquals(Color(0xFF8E9BFF), dark.primary)
        assertEquals(Color(0xFF1B2040), dark.surface)
        assertEquals(Color(0xFF11152A), dark.onPrimary)
    }

    @Test
    fun gradientsMatchDesign() {
        val brand = gradient(0x3949C8, 0x6A4BD8, 0x9B4DCB)
        val gold = gradient(0xF2A516, 0xF57C4B)
        assertEquals(brand, LightGradients.brand)
        assertEquals(brand, DarkGradients.brand)
        assertEquals(gold, LightGradients.gold)
        assertEquals(gold, DarkGradients.gold)
        assertEquals(gradient(0x3949C8, 0x7B4FE0, 0xB94A9E), LightGradients.text)
        assertEquals(gradient(0x9AA6FF, 0xC3A2FF, 0xFF9CC8), DarkGradients.text)
        assertNotEquals(LightGradients.text, DarkGradients.text)
    }
}
