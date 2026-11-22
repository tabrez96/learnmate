package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

/** Two or three exclusive options in one pill (e.g. "Learn and test" / "Test only"). */
@Composable
fun SegmentedControl(
    options: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    Row(
        modifier
            .heightIn(min = 44.dp)
            .height(IntrinsicSize.Min)
            .background(colors.paper, LearnmateShapes.pill)
            .border(1.dp, colors.line, LearnmateShapes.pill)
            .padding(3.dp)
            .selectableGroup(),
    ) {
        options.forEachIndexed { i, option ->
            val selected = i == selectedIndex
            val interaction = remember { MutableInteractionSource() }
            val focused by interaction.collectIsFocusedAsState()
            val shadow = Shadow(4.dp, Color.Black.copy(alpha = 0.12f), offset = DpOffset(0.dp, 1.dp))
            val look =
                if (selected) {
                    Modifier.dropShadow(LearnmateShapes.pill, shadow).background(colors.card, LearnmateShapes.pill)
                } else {
                    Modifier
                }
            Box(
                Modifier
                    .fillMaxHeight()
                    .focusRing(focused, colors.blue, LearnmateShapes.pill)
                    .clip(LearnmateShapes.pill)
                    .then(look)
                    .selectable(
                        selected = selected,
                        role = Role.RadioButton,
                        interactionSource = interaction,
                        indication = ripple(),
                        onClick = { onSelect(i) },
                    ).padding(horizontal = 16.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    option,
                    color = if (selected) colors.ink else colors.inkSoft,
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium),
                )
            }
        }
    }
}
