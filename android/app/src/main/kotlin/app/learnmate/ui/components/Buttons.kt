package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.LightColors
import app.learnmate.ui.theme.gradientGlow

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val shape = LearnmateShapes.button
    val glow = if (enabled) Modifier.gradientGlow(LearnmateTheme.surfaces, shape) else Modifier
    ButtonBase(
        text,
        onClick,
        modifier,
        enabled,
        LearnmateSpacing.buttonMinHeight,
        24.dp,
        Color.White,
        glow.background(LearnmateTheme.gradients.brand, shape),
    )
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val shape = LearnmateShapes.button
    val colors = LearnmateTheme.colors
    ButtonBase(
        text,
        onClick,
        modifier,
        enabled,
        LearnmateSpacing.buttonMinHeight,
        24.dp,
        colors.blueText,
        Modifier.background(colors.blueTint, shape).border(1.dp, colors.blue.copy(alpha = 0.35f), shape),
    )
}

@Composable
fun GhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) = ButtonBase(text, onClick, modifier, enabled, LearnmateSpacing.ghostButtonMinHeight, 16.dp, LearnmateTheme.colors.blue, Modifier)

/** White button for a [GradientHeroCard]; the hero gradient is the same in both modes, so the text colour is too. */
@Composable
fun HeroButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) = ButtonBase(
    text,
    onClick,
    modifier,
    enabled,
    LearnmateSpacing.buttonMinHeight,
    24.dp,
    LightColors.blueText,
    Modifier.background(Color.White, LearnmateShapes.button),
)

@Composable
private fun ButtonBase(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier,
    enabled: Boolean,
    minHeight: Dp,
    horizontalPadding: Dp,
    textColor: Color,
    surface: Modifier,
) {
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    Box(
        modifier
            .defaultMinSize(minHeight = minHeight)
            .alpha(if (enabled) 1f else 0.4f)
            .focusRing(focused, LearnmateTheme.colors.blue, LearnmateShapes.button)
            .then(surface)
            .clip(LearnmateShapes.button)
            .clickable(interaction, ripple(), enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = horizontalPadding),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = textColor, style = MaterialTheme.typography.labelLarge, textAlign = TextAlign.Center)
    }
}
