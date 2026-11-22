package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

/** Material row with a checkbox: file type, name, meta line ("Added 12 Nov"), trailing chip ("New" or last result). */
@Composable
fun LibraryRow(
    fileType: String,
    name: String,
    meta: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    trailing: @Composable (() -> Unit)? = null,
) {
    val colors = LearnmateTheme.colors
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    Row(
        modifier
            .fillMaxWidth()
            .heightIn(min = 64.dp)
            .focusRing(focused, colors.blue, LearnmateShapes.button)
            .optionSurface(LearnmateShapes.button, if (checked) colors.blueTint else colors.card, checked, colors.blue, colors.line)
            .toggleable(
                value = checked,
                role = Role.Checkbox,
                interactionSource = interaction,
                indication = ripple(),
                onValueChange = onCheckedChange,
            ).padding(horizontal = 16.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val box = RoundedCornerShape(6.dp)
        Box(
            Modifier
                .size(22.dp)
                .then(if (checked) Modifier.background(colors.blue, box) else Modifier.border(2.dp, colors.line, box))
                .clearAndSetSemantics {},
            contentAlignment = Alignment.Center,
        ) {
            if (checked) CheckGlyph(Color.White)
        }
        Text(
            fileType.uppercase(),
            Modifier
                .width(44.dp)
                .background(colors.blueTint, RoundedCornerShape(8.dp))
                .padding(horizontal = 6.dp, vertical = 3.dp),
            color = colors.blueText,
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
        )
        Column(Modifier.weight(1f)) {
            Text(name, color = colors.ink, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge)
            Text(meta, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
        }
        trailing?.invoke()
    }
}
