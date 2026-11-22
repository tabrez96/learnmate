package app.learnmate.ui.components

import app.learnmate.ui.theme.DarkColors
import app.learnmate.ui.theme.LightColors
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class ChipToneTest {
    @Test
    fun missedIsGrey() {
        assertEquals(LightColors.line to LightColors.inkSoft, ChipTone.Missed.colors(LightColors))
        assertEquals(DarkColors.line to DarkColors.inkSoft, ChipTone.Missed.colors(DarkColors))
    }

    @Test
    fun tonesMapToTheirTokens() {
        val c = LightColors
        assertEquals(c.blueTint to c.blueText, ChipTone.Blue.colors(c))
        assertEquals(c.greenTint to c.greenText, ChipTone.Ok.colors(c))
        assertEquals(c.amberTint to c.amberText, ChipTone.Warn.colors(c))
        assertEquals(c.redTint to c.redText, ChipTone.Bad.colors(c))
    }

    @Test
    fun sessionPillLabel_formatsMinutes() {
        assertEquals("Session on · 24 min", sessionPillLabel(24))
    }
}
