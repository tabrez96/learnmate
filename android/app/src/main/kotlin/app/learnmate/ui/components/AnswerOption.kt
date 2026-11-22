package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.selectable
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

enum class AnswerState { Default, Selected, Right, Wrong }

/** Text shown on the option so right and wrong never rely on colour alone. */
fun AnswerState.feedbackLabel(): String? =
    when (this) {
        AnswerState.Right -> "Correct!"
        AnswerState.Wrong -> "Your answer"
        else -> null
    }

/** Large answer button for S06: letter, text, and after checking a feedback label. 84 dp high at least. */
@Composable
fun AnswerOption(
    letter: Char,
    text: String,
    state: AnswerState,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val colors = LearnmateTheme.colors
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    val shape = LearnmateShapes.tile
    val (fill, edge, circle, letterColor) =
        when (state) {
            AnswerState.Default -> listOf(colors.card, colors.line, colors.paper, colors.inkSoft)
            AnswerState.Selected -> listOf(colors.blueTint, colors.blue, colors.blue, Color.White)
            AnswerState.Right -> listOf(colors.greenTint, colors.green, colors.green, Color.White)
            AnswerState.Wrong -> listOf(colors.redTint, colors.red, colors.red, Color.White)
        }
    val label = state.feedbackLabel()
    val frame =
        if (state == AnswerState.Right || state == AnswerState.Wrong) {
            Modifier.clip(shape).background(fill).border(2.dp, edge, shape)
        } else {
            Modifier.optionSurface(shape, fill, state == AnswerState.Selected, colors.blue, colors.line)
        }
    Row(
        modifier
            .fillMaxWidth()
            .padding(4.dp)
            .heightIn(min = 84.dp)
            .focusRing(focused, colors.blue, shape)
            .then(frame)
            .selectable(
                selected = state == AnswerState.Selected,
                enabled = enabled,
                role = Role.RadioButton,
                interactionSource = interaction,
                indication = ripple(),
                onClick = onClick,
            ).semantics { stateDescription = label ?: if (state == AnswerState.Selected) "Selected" else "Not selected" }
            .padding(horizontal = 20.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(40.dp).background(circle, CircleShape).clearAndSetSemantics {}, contentAlignment = Alignment.Center) {
            Text(letter.toString(), color = letterColor, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
        }
        Text(text, Modifier.weight(1f), color = colors.ink, style = MaterialTheme.typography.bodyLarge)
        if (label != null) LearnmateChip(label, if (state == AnswerState.Right) ChipTone.Ok else ChipTone.Bad)
    }
}
