package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

data class SideNavItem(
    val label: String,
    val icon: String? = null,
)

/** Vertical section navigation for S09. Active item: Blue tint fill plus a 4x20 dp Blue bar inset 8 dp from the left. */
@Composable
fun SideNav(
    items: List<SideNavItem>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    Column(modifier.width(220.dp).selectableGroup(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        items.forEachIndexed { i, item ->
            val active = i == selectedIndex
            val interaction = remember { MutableInteractionSource() }
            val focused by interaction.collectIsFocusedAsState()
            Box(
                Modifier
                    .fillMaxWidth()
                    .heightIn(min = 44.dp)
                    .focusRing(focused, colors.blue, LearnmateShapes.button)
                    .clip(LearnmateShapes.button)
                    .background(if (active) colors.blueTint else Color.Transparent)
                    .selectable(
                        selected = active,
                        role = Role.Tab,
                        interactionSource = interaction,
                        indication = ripple(),
                        onClick = { onSelect(i) },
                    ),
            ) {
                if (active) {
                    Box(
                        Modifier
                            .align(Alignment.CenterStart)
                            .offset(x = 8.dp)
                            .size(width = 4.dp, height = 20.dp)
                            .background(colors.blue, LearnmateShapes.pill),
                    )
                }
                Row(
                    Modifier.align(Alignment.CenterStart).padding(start = 20.dp, end = 12.dp, top = 8.dp, bottom = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (item.icon != null) Text(item.icon, Modifier.clearAndSetSemantics {})
                    Text(
                        item.label,
                        color = if (active) colors.blueText else colors.inkSoft,
                        style = MaterialTheme.typography.bodyLarge.copy(fontWeight = if (active) FontWeight.Bold else FontWeight.Medium),
                    )
                }
            }
        }
    }
}
