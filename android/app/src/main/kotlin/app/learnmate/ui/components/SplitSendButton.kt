package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.collapse
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.expand
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.gradientGlow

/**
 * "Send" with an arrow part that opens a menu with "Send and check outside the books".
 * The arrow is the Compose stand-in for a menu button (dropdown role, expanded or collapsed), and the menu rows
 * are radio-role items. The books option is always the selected one: a choice never sticks past one message.
 */
@Composable
fun SplitSendButton(
    onSend: () -> Unit,
    onSendOutside: () -> Unit,
    showMenu: Boolean,
    enabled: Boolean,
    modifier: Modifier = Modifier,
) {
    val colors = LearnmateTheme.colors
    val shape = LearnmateShapes.button
    var open by remember { mutableStateOf(false) }
    val glow = if (enabled) Modifier.gradientGlow(LearnmateTheme.surfaces, shape) else Modifier
    Row(
        modifier
            .height(IntrinsicSize.Min)
            .defaultMinSize(minHeight = LearnmateSpacing.buttonMinHeight)
            .alpha(if (enabled) 1f else 0.4f)
            .then(glow)
            .clip(shape)
            .background(LearnmateTheme.gradients.brand, shape),
    ) {
        Box(
            Modifier
                .testTag("send")
                .defaultMinSize(minHeight = LearnmateSpacing.buttonMinHeight)
                .fillMaxHeight()
                .clickable(enabled = enabled, role = Role.Button, onClick = onSend)
                .padding(horizontal = 24.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("Send", color = Color.White, style = MaterialTheme.typography.labelLarge)
        }
        if (showMenu) {
            Box(Modifier.width(1.dp).fillMaxHeight().background(Color.White.copy(alpha = 0.35f)))
            Box {
                Box(
                    Modifier
                        .testTag("sendArrow")
                        .width(44.dp)
                        .fillMaxHeight()
                        .clickable(enabled = enabled, onClick = { open = !open })
                        .semantics {
                            contentDescription = "More send options"
                            role = Role.DropdownList
                            stateDescription = if (open) "Expanded" else "Collapsed"
                            expand {
                                open = true
                                true
                            }
                            collapse {
                                open = false
                                true
                            }
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Text("▾", color = Color.White, style = MaterialTheme.typography.labelLarge, modifier = Modifier.clearAndSetSemantics {})
                }
                DropdownMenu(
                    expanded = open,
                    onDismissRequest = { open = false },
                    shape = LearnmateShapes.card,
                    containerColor = colors.card,
                    modifier = Modifier.widthIn(min = 320.dp),
                ) {
                    Column(
                        Modifier
                            .testTag("sendMenu")
                            .selectableGroup()
                            .padding(horizontal = 8.dp)
                            .onPreviewKeyEvent {
                                val escape = it.key == Key.Escape && it.type == KeyEventType.KeyDown
                                if (escape) open = false
                                escape
                            },
                    ) {
                        MenuOption("📖", "Send", "Answer only from your books", selected = true) {
                            open = false
                            onSend()
                        }
                        MenuOption(
                            "🌐",
                            "Send and check outside the books",
                            "Looks it up on trusted sites. The answer is marked so you know.",
                            selected = false,
                        ) {
                            open = false
                            onSendOutside()
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MenuOption(
    icon: String,
    title: String,
    subtitle: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = LearnmateTheme.colors
    Row(
        Modifier
            .clip(LearnmateShapes.button)
            .background(if (selected) colors.blueTint else Color.Transparent, LearnmateShapes.button)
            .selectable(selected = selected, role = Role.RadioButton, onClick = onClick, indication = ripple(), interactionSource = null)
            .padding(14.dp),
        horizontalArrangement =
            androidx.compose.foundation.layout.Arrangement
                .spacedBy(12.dp),
    ) {
        Text(icon, modifier = Modifier.clearAndSetSemantics {})
        Column {
            Text(title, color = colors.ink, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            Text(subtitle, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
        }
    }
}
