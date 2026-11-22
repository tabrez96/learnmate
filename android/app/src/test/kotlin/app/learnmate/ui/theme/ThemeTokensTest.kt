package app.learnmate.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.shadow.Shadow
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
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

    private fun assertShadow(
        s: Shadow,
        radius: Int,
        spread: Int,
        y: Int,
        color: Color,
    ) {
        assertEquals(radius.dp, s.radius)
        assertEquals(spread.dp, s.spread)
        assertEquals(DpOffset(0.dp, y.dp), s.offset)
        assertEquals(color, s.color)
    }

    @Test
    fun typographyMatchesDesign() {
        val t = learnmateTypography(compact = false)
        assertEquals(32.sp, t.headlineLarge.fontSize)
        assertEquals(37.sp, t.headlineLarge.lineHeight)
        assertEquals(FontWeight.ExtraBold, t.headlineLarge.fontWeight)
        assertEquals((-0.8).sp, t.headlineLarge.letterSpacing)
        assertEquals(20.sp, t.titleLarge.fontSize)
        assertEquals(FontWeight.Bold, t.titleLarge.fontWeight)
        assertEquals((-0.3).sp, t.titleLarge.letterSpacing)
        assertEquals(16.sp, t.bodyLarge.fontSize)
        assertEquals(15.sp, t.bodyMedium.fontSize)
        assertEquals(13.sp, t.bodySmall.fontSize)
        assertEquals(96.sp, t.displayLarge.fontSize)
        assertEquals(FontWeight.Black, t.displayLarge.fontWeight)
    }

    @Test
    fun compactTypographyShrinksH1() {
        val t = learnmateTypography(compact = true)
        assertEquals(28.sp, t.headlineLarge.fontSize)
        assertEquals(20.sp, t.titleLarge.fontSize)
    }

    @Test
    fun spacingMatchesDesign() {
        with(LearnmateSpacing) {
            assertEquals(
                listOf(4.dp, 24.dp, 32.dp, 20.dp),
                listOf(base, screenPaddingVertical, screenPaddingHorizontal, screenPaddingPhone),
            )
            assertEquals(listOf(16.dp, 24.dp, 20.dp), listOf(blockGap, blockGapLarge, cardPadding))
            assertEquals(listOf(64.dp, 12.dp, 16.dp), listOf(topBarHeight, topBarTopInset, topBarSideInset))
            assertEquals(0.72f, TOP_BAR_ALPHA)
        }
    }

    @Test
    fun shapesMatchDesign() {
        assertEquals(RoundedCornerShape(24.dp), LearnmateShapes.card)
        assertEquals(RoundedCornerShape(20.dp), LearnmateShapes.tile)
        assertEquals(RoundedCornerShape(20.dp), LearnmateShapes.topBar)
        assertEquals(RoundedCornerShape(16.dp), LearnmateShapes.button)
        assertEquals(RoundedCornerShape(14.dp), LearnmateShapes.input)
        assertEquals(RoundedCornerShape(24.dp), LearnmateShapes.dialog)
        assertEquals(RoundedCornerShape(percent = 50), LearnmateShapes.pill)
        with(LearnmateMaterialShapes) {
            assertEquals(
                listOf(LearnmateShapes.input, LearnmateShapes.button, LearnmateShapes.card, LearnmateShapes.card, LearnmateShapes.dialog),
                listOf(extraSmall, small, medium, large, extraLarge),
            )
        }
    }

    @Test
    fun surfacesMatchDesign() {
        val glow = Color(0xFF6A4BD8).copy(alpha = 0.55f)
        assertEquals(LightColors.ink.copy(alpha = 0.06f), LightSurfaces.cardBorder)
        assertEquals(Color.White.copy(alpha = 0.07f), DarkSurfaces.cardBorder)
        assertEquals(2, LightSurfaces.cardShadows.size)
        assertShadow(LightSurfaces.cardShadows[0], 24, -6, 8, LightColors.ink.copy(alpha = 0.10f))
        assertShadow(LightSurfaces.cardShadows[1], 48, -24, 24, LightColors.blue.copy(alpha = 0.18f))
        assertNull(LightSurfaces.cardHighlight)
        assertEquals(1, DarkSurfaces.cardShadows.size)
        assertShadow(DarkSurfaces.cardShadows[0], 32, -8, 16, Color.Black.copy(alpha = 0.45f))
        assertNotNull(DarkSurfaces.cardHighlight)
        assertShadow(LightSurfaces.glow, 24, -8, 8, glow)
        assertShadow(DarkSurfaces.glow, 24, -8, 8, glow)
        assertEquals(LightColors.blue.copy(alpha = 0.14f), LightSurfaces.selectedHalo)
        assertEquals(DarkColors.blue.copy(alpha = 0.14f), DarkSurfaces.selectedHalo)
        assertEquals(0.10f, LightSurfaces.pageGlowBlue.alpha, 0.005f)
        assertEquals(0.10f, LightSurfaces.pageGlowViolet.alpha, 0.005f)
        assertEquals(0.24f, DarkSurfaces.pageGlowBlue.alpha, 0.005f)
        assertEquals(0.24f, DarkSurfaces.pageGlowViolet.alpha, 0.005f)
    }
}
