package app.learnmate.ui.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@Composable
private fun ColorTokenSheet() {
    Column(
        Modifier.background(LearnmateTheme.colors.paper).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        val colors =
            LearnmateTheme.colors.tokens().map { (name, color) ->
                Triple(name, "#%06X".format(color.toArgb() and 0xFFFFFF), SolidColor(color))
            }
        val gradients =
            LearnmateTheme.gradients.let {
                listOf(
                    Triple("Brand gradient", "135deg", it.brand),
                    Triple("Text gradient", "135deg", it.text),
                    Triple("Gold gradient", "135deg", it.gold),
                )
            }
        (colors + gradients).chunked(6).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { (name, caption, brush) -> Swatch(name, caption, brush) }
            }
        }
    }
}

@Composable
private fun Swatch(
    name: String,
    caption: String,
    brush: Brush,
) {
    val shape = RoundedCornerShape(12.dp)
    Column(Modifier.width(180.dp)) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(56.dp)
                .clip(shape)
                .background(brush)
                .border(1.dp, LearnmateTheme.colors.line, shape),
        )
        Text(name, color = LearnmateTheme.colors.ink, fontSize = 14.sp)
        Text(caption, color = LearnmateTheme.colors.inkSoft, fontSize = 12.sp)
    }
}

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w1280dp-h800dp-mdpi")
class ColorTokenSheetScreenshotTest {
    @Test
    fun lightSheet() =
        captureRoboImage("src/test/screenshots/color_tokens_light.png") {
            LearnmateTheme(darkTheme = false) { ColorTokenSheet() }
        }

    @Test
    fun darkSheet() =
        captureRoboImage("src/test/screenshots/color_tokens_dark.png") { LearnmateTheme(darkTheme = true) { ColorTokenSheet() } }
}
