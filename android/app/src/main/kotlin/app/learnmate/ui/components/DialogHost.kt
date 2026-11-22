package app.learnmate.ui.components

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.isTraversalGroup
import androidx.compose.ui.semantics.paneTitle
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.DarkColors
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.cardSurface

/**
 * Shows [content]; when [title] is non-null, blurs [content], dims it with a scrim and centres the dialog card on top.
 * Tapping the scrim or pressing back calls [onDismiss]. Blur renders on API 31+; below that the scrim alone dims.
 */
@Composable
fun LearnmateDialogHost(
    title: String?,
    onDismiss: () -> Unit,
    content: @Composable () -> Unit,
    dialog: @Composable ColumnScope.() -> Unit,
) {
    val colors = LearnmateTheme.colors
    val dismiss by rememberUpdatedState(onDismiss)
    val focusManager = LocalFocusManager.current
    // Blur and cleared semantics don't remove keyboard focus, so drop it from the background fields.
    LaunchedEffect(title != null) { if (title != null) focusManager.clearFocus(force = true) }
    Box(Modifier.fillMaxSize()) {
        val behind = if (title != null) Modifier.blur(8.dp).clearAndSetSemantics {} else Modifier
        Box(Modifier.fillMaxSize().then(behind)) { content() }
        if (title != null) {
            val scrim = if (colors == DarkColors) Color.Black.copy(alpha = 0.55f) else colors.ink.copy(alpha = 0.35f)
            Box(
                Modifier
                    .fillMaxSize()
                    .background(scrim)
                    .pointerInput(Unit) { detectTapGestures { dismiss() } },
            )
            Column(
                Modifier
                    .align(Alignment.Center)
                    .widthIn(max = 520.dp)
                    .padding(24.dp)
                    .cardSurface(LearnmateTheme.surfaces, colors.card, LearnmateShapes.dialog)
                    .pointerInput(Unit) { detectTapGestures {} }
                    .padding(24.dp)
                    .semantics {
                        paneTitle = title
                        isTraversalGroup = true
                    },
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(title, Modifier.semantics { heading() }, color = colors.ink, style = MaterialTheme.typography.titleLarge)
                dialog()
            }
        }
    }
    BackHandler(enabled = title != null, onBack = onDismiss)
}
