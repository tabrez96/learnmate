package app.learnmate.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import app.learnmate.R
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.cardSurface

@Composable
fun Wordmark(modifier: Modifier = Modifier) {
    val colors = LearnmateTheme.colors
    val gradients = LearnmateTheme.gradients
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.size(34.dp).clip(RoundedCornerShape(9.dp))) {
            Image(painterResource(R.drawable.ic_launcher_background), null, Modifier.fillMaxSize())
            Image(painterResource(R.drawable.ic_launcher_foreground), null, Modifier.fillMaxSize())
        }
        Text(
            buildAnnotatedString {
                withStyle(SpanStyle(color = colors.ink)) { append("Learn") }
                withStyle(SpanStyle(brush = gradients.text)) { append("mate") }
            },
            style = MaterialTheme.typography.titleLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** Floating top bar. No backdrop blur is drawn (Compose has none without a new dependency); 72% card colour and the shadow stand in. */
@Composable
fun LearnmateTopBar(
    modifier: Modifier = Modifier,
    actions: @Composable RowScope.() -> Unit,
) {
    val colors = LearnmateTheme.colors
    Row(
        modifier
            .fillMaxWidth()
            .padding(
                top = LearnmateSpacing.topBarTopInset,
                start = LearnmateSpacing.topBarSideInset,
                end = LearnmateSpacing.topBarSideInset,
            ).height(LearnmateSpacing.topBarHeight)
            .cardSurface(LearnmateTheme.surfaces, colors.card.copy(alpha = LearnmateSpacing.TOP_BAR_ALPHA), LearnmateShapes.topBar)
            .padding(horizontal = 20.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Wordmark(Modifier.weight(1f))
        Spacer(Modifier.width(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically, content = actions)
    }
}
