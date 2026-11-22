package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme

@Composable
fun LearnmateProgressBar(
    progress: Float,
    modifier: Modifier = Modifier,
    track: Color = LearnmateTheme.colors.line,
    fill: Brush = LearnmateTheme.gradients.brand,
) {
    val p = if (progress.isNaN()) 0f else progress.coerceIn(0f, 1f)
    Box(
        modifier
            .fillMaxWidth()
            .height(LearnmateSpacing.progressBarHeight)
            .clip(LearnmateShapes.pill)
            .background(track)
            .semantics { progressBarRangeInfo = ProgressBarRangeInfo(p, 0f..1f) },
    ) {
        if (p > 0f) {
            Box(
                Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(p)
                    .clip(LearnmateShapes.pill)
                    .background(fill),
            )
        }
    }
}
