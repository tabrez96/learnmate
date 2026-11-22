package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.dropShadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.shadow.Shadow
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

private val SunAmber = Color(0xFFF2A516)

/** Sun/moon light-dark control. One switch: checked means dark mode. */
@Composable
fun ThemeSwitch(
    dark: Boolean,
    onDarkChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    Row(
        modifier
            .size(width = 90.dp, height = 44.dp)
            .focusRing(focused, colors.blue, LearnmateShapes.pill)
            .clip(LearnmateShapes.pill)
            .background(colors.paper)
            .border(1.dp, colors.line, LearnmateShapes.pill)
            .toggleable(
                value = dark,
                interactionSource = interaction,
                indication = ripple(),
                role = Role.Switch,
                onValueChange = onDarkChange,
            ).semantics { contentDescription = "Dark mode" }
            .padding(3.dp),
    ) {
        Slot(active = !dark) { SunGlyph(if (!dark) SunAmber else colors.inkSoft) }
        Slot(active = dark) { MoonGlyph(if (dark) colors.blueText else colors.inkSoft) }
    }
}

@Composable
private fun RowScope.Slot(
    active: Boolean,
    glyph: @Composable () -> Unit,
) {
    val shadow = Shadow(4.dp, Color.Black.copy(alpha = 0.12f), offset = DpOffset(0.dp, 1.dp))
    val look =
        if (active) Modifier.dropShadow(CircleShape, shadow).background(LearnmateTheme.colors.card, CircleShape) else Modifier
    Box(Modifier.weight(1f).fillMaxHeight().then(look), contentAlignment = Alignment.Center) { glyph() }
}
