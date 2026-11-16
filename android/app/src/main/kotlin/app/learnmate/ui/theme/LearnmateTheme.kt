package app.learnmate.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

val LocalLearnmateColors = staticCompositionLocalOf { LightColors }
val LocalLearnmateGradients = staticCompositionLocalOf { LightGradients }

object LearnmateTheme {
    val colors: LearnmateColors
        @Composable @ReadOnlyComposable
        get() = LocalLearnmateColors.current
    val gradients: LearnmateGradients
        @Composable @ReadOnlyComposable
        get() = LocalLearnmateGradients.current
}

@Composable
fun LearnmateTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colors = if (darkTheme) DarkColors else LightColors
    val gradients = if (darkTheme) DarkGradients else LightGradients
    CompositionLocalProvider(LocalLearnmateColors provides colors, LocalLearnmateGradients provides gradients) {
        MaterialTheme(colorScheme = colors.toColorScheme(darkTheme), content = content)
    }
}

internal fun LearnmateColors.toColorScheme(dark: Boolean): ColorScheme {
    val onAccent = if (dark) DarkColors.paper else Color.White
    return (if (dark) darkColorScheme() else lightColorScheme()).copy(
        primary = blue,
        onPrimary = onAccent,
        primaryContainer = blueTint,
        onPrimaryContainer = blueText,
        secondary = green,
        onSecondary = onAccent,
        secondaryContainer = greenTint,
        onSecondaryContainer = greenText,
        tertiaryContainer = amberTint,
        onTertiaryContainer = amberText,
        background = paper,
        onBackground = ink,
        surface = card,
        onSurface = ink,
        surfaceVariant = paper,
        onSurfaceVariant = inkSoft,
        outline = line,
        outlineVariant = line,
        error = red,
        onError = onAccent,
        errorContainer = redTint,
        onErrorContainer = redText,
    )
}
