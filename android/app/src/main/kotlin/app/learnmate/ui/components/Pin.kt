package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

/** Four digit boxes showing the typed digits; the next empty box is outlined. */
@Composable
fun PinDigitBoxes(
    digits: String,
    modifier: Modifier = Modifier,
    length: Int = 4,
) {
    val colors = LearnmateTheme.colors
    Row(
        modifier.clearAndSetSemantics { contentDescription = "PIN " + digits.take(length).toList().joinToString(" ") },
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        for (i in 0 until length) {
            val next = i == digits.length
            Box(
                Modifier
                    .size(width = 64.dp, height = 76.dp)
                    .background(colors.card, LearnmateShapes.tile)
                    .border(if (next) 2.dp else 1.dp, if (next) colors.blue else colors.line, LearnmateShapes.tile),
                contentAlignment = Alignment.Center,
            ) {
                Text(digits.getOrNull(i)?.toString() ?: "", color = colors.ink, style = MaterialTheme.typography.headlineLarge)
            }
        }
    }
}

/** Masked progress dots for the PIN pad. */
@Composable
fun PinDots(
    filled: Int,
    modifier: Modifier = Modifier,
    length: Int = 4,
    error: Boolean = false,
) {
    val colors = LearnmateTheme.colors
    val count = filled.coerceIn(0, length)
    Row(
        modifier.clearAndSetSemantics {
            contentDescription = "$count of $length digits entered" + if (error) ", PIN not accepted" else ""
        },
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        for (i in 0 until length) {
            val dot = Modifier.size(16.dp)
            if (i < count) {
                Box(dot.background(if (error) colors.red else colors.blue, CircleShape))
            } else {
                Box(dot.border(2.dp, if (error) colors.red else colors.line, CircleShape))
            }
        }
    }
}

sealed interface KeypadKey {
    data class Digit(
        val value: Int,
    ) : KeypadKey

    data object Delete : KeypadKey

    data object Blank : KeypadKey
}

/** Keypad layout: 1-9, then blank, 0, Delete. */
val KeypadLayout: List<List<KeypadKey>> =
    listOf(
        listOf(KeypadKey.Digit(1), KeypadKey.Digit(2), KeypadKey.Digit(3)),
        listOf(KeypadKey.Digit(4), KeypadKey.Digit(5), KeypadKey.Digit(6)),
        listOf(KeypadKey.Digit(7), KeypadKey.Digit(8), KeypadKey.Digit(9)),
        listOf(KeypadKey.Blank, KeypadKey.Digit(0), KeypadKey.Delete),
    )

private val KeySize = Modifier.size(width = 88.dp, height = 72.dp)

/** 3x4 keypad with 88x72 dp keys. */
@Composable
fun PinKeypad(
    onDigit: (Int) -> Unit,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        KeypadLayout.forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { key ->
                    when (key) {
                        KeypadKey.Blank -> Spacer(KeySize)
                        is KeypadKey.Digit -> Key(key.value.toString(), enabled, { onDigit(key.value) })
                        KeypadKey.Delete -> Key("Delete", enabled, onDelete)
                    }
                }
            }
        }
    }
}

@Composable
private fun Key(
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val colors = LearnmateTheme.colors
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    val isDigit = label.length == 1
    Box(
        KeySize
            .focusRing(focused, colors.blue, LearnmateShapes.tile)
            .clip(LearnmateShapes.tile)
            .background(colors.card)
            .border(1.dp, colors.line, LearnmateShapes.tile)
            .clickable(enabled = enabled, role = Role.Button, interactionSource = interaction, indication = ripple(), onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label,
            color = if (isDigit) colors.ink else colors.inkSoft,
            style = if (isDigit) MaterialTheme.typography.headlineMedium else MaterialTheme.typography.labelLarge,
        )
    }
}
