package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
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
import androidx.compose.ui.draw.dropShadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.shadow.Shadow
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

/** Row of subject tiles: a radio group, one subject per session. */
@Composable
fun SubjectTileGroup(
    modifier: Modifier = Modifier,
    content: @Composable RowScope.() -> Unit,
) {
    Row(
        modifier.horizontalScroll(rememberScrollState()).selectableGroup().padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        content = content,
    )
}

/** Radio tile: icon, name, material count and latest grade ("Nothing yet" when null). */
@Composable
fun SubjectTile(
    icon: String,
    name: String,
    materialCount: Int,
    latestGrade: String?,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    Column(
        modifier
            .width(180.dp)
            .focusRing(focused, colors.blue, LearnmateShapes.tile)
            .optionSurface(LearnmateShapes.tile, colors.card, selected, colors.blue, colors.line)
            .selectable(
                selected = selected,
                role = Role.RadioButton,
                interactionSource = interaction,
                indication = ripple(),
                onClick = onClick,
            ).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(icon, fontSize = 24.sp, modifier = Modifier.clearAndSetSemantics {})
            Spacer(Modifier.weight(1f))
            Box(
                Modifier.size(20.dp).border(2.dp, if (selected) colors.blue else colors.line, CircleShape).clearAndSetSemantics {},
                contentAlignment = Alignment.Center,
            ) {
                if (selected) Box(Modifier.size(10.dp).background(colors.blue, CircleShape))
            }
        }
        Text(name, color = colors.ink, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
        Text(materialCountLabel(materialCount), color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
        Text(latestGrade ?: "Nothing yet", color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
    }
}

/** Dashed-look tile that adds a subject. Sits in the group but is a button, not a radio. */
@Composable
fun NewSubjectTile(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    Box(
        modifier
            .width(180.dp)
            .heightIn(min = 120.dp)
            .clip(LearnmateShapes.tile)
            .border(1.5.dp, colors.blue.copy(alpha = 0.4f), LearnmateShapes.tile)
            .clickable(role = Role.Button, onClick = onClick)
            .padding(16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text("+ New subject", color = colors.blueText, style = MaterialTheme.typography.titleSmall)
    }
}

fun materialCountLabel(n: Int): String = if (n == 1) "1 material" else "$n materials"

/**
 * Surface for selectable rows and options: fill, 1 dp Line border, or when selected a 2 dp Blue border with a 4 dp
 * Blue halo at 14% drawn outside the bounds, so the item keeps its size.
 */
internal fun Modifier.optionSurface(
    shape: Shape,
    fill: Color,
    selected: Boolean,
    blue: Color,
    line: Color,
): Modifier =
    (if (selected) dropShadow(shape, Shadow(0.dp, blue.copy(alpha = 0.14f), spread = 4.dp)) else this)
        .clip(shape)
        .background(fill)
        .border(if (selected) 2.dp else 1.dp, if (selected) blue else line, shape)
