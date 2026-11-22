package app.learnmate.ui.theme

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.learnmate.R
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@Composable
internal fun TokenSheet() {
    Column(
        Modifier
            .fillMaxSize()
            .pageBackground(LearnmateTheme.colors.paper, LearnmateTheme.surfaces)
            .padding(LearnmateSpacing.screenPaddingVertical),
        verticalArrangement = Arrangement.spacedBy(LearnmateSpacing.blockGapLarge),
    ) {
        SectionTitle("Colours")
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
        TypeSection()
        ShapesSection()
        SurfacesSection()
    }
}

@Composable
private fun SectionTitle(text: String) = Text(text, color = LearnmateTheme.colors.ink, style = MaterialTheme.typography.titleLarge)

@Composable
private fun TypeSection() {
    val ink = LearnmateTheme.colors.ink
    val type = MaterialTheme.typography
    SectionTitle("Type")
    Text("Heading one", color = ink, style = type.headlineLarge)
    Text("Heading two", color = ink, style = type.titleLarge)
    Text("Card title", color = ink, style = type.titleMedium)
    Text("Body text for lessons", color = ink, style = type.bodyLarge)
    Text("Small text 15", color = ink, style = type.bodyMedium)
    Text("Small text 13", color = ink, style = type.bodySmall)
    Text("92%", style = type.displayLarge.copy(brush = LearnmateTheme.gradients.text))
}

@Composable
private fun ShapesSection() {
    SectionTitle("Shapes")
    val shapes =
        listOf(
            "Card 24" to LearnmateShapes.card,
            "Dialog 24" to LearnmateShapes.dialog,
            "Tile 20" to LearnmateShapes.tile,
            "Top bar 20" to LearnmateShapes.topBar,
            "Button 16" to LearnmateShapes.button,
            "Input 14" to LearnmateShapes.input,
            "Pill" to LearnmateShapes.pill,
        )
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        shapes.forEach { (name, shape) ->
            Column {
                Box(
                    Modifier
                        .size(120.dp, 72.dp)
                        .background(LearnmateTheme.colors.blueTint, shape)
                        .border(1.dp, LearnmateTheme.colors.line, shape),
                )
                Text(name, color = LearnmateTheme.colors.inkSoft, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun SurfacesSection() {
    val surfaces = LearnmateTheme.surfaces
    val colors = LearnmateTheme.colors
    SectionTitle("Surfaces")
    Row(
        Modifier.padding(24.dp),
        horizontalArrangement = Arrangement.spacedBy(32.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(
            Modifier.width(320.dp).cardSurface(surfaces, colors.card).padding(LearnmateSpacing.cardPadding),
        ) {
            Text("Card with shadow", color = colors.ink, style = MaterialTheme.typography.titleMedium)
            Text("Layered shadow and a hairline border", color = colors.inkSoft, style = MaterialTheme.typography.bodyMedium)
        }
        Box(
            Modifier
                .height(LearnmateSpacing.buttonMinHeight)
                .gradientGlow(surfaces, LearnmateShapes.button)
                .background(LearnmateTheme.gradients.brand, LearnmateShapes.button)
                .padding(horizontal = 24.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("Start session", color = Color.White, style = MaterialTheme.typography.labelLarge)
        }
        Box(
            Modifier
                .size(240.dp, 84.dp)
                .selectedHalo(surfaces, LearnmateShapes.tile)
                .background(colors.blueTint, LearnmateShapes.tile),
            contentAlignment = Alignment.Center,
        ) {
            Text("Selected option", color = colors.blueText, style = MaterialTheme.typography.labelLarge)
        }
        Box(Modifier.size(108.dp).clip(LearnmateShapes.tile)) {
            Image(painterResource(R.drawable.ic_launcher_background), null)
            Image(painterResource(R.drawable.ic_launcher_foreground), null)
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
@Config(qualifiers = "w1280dp-h1500dp-mdpi")
class TokenSheetScreenshotTest {
    @Test
    fun lightSheet() =
        captureRoboImage("src/test/screenshots/token_sheet_light.png") {
            LearnmateTheme(darkTheme = false, compact = false) { TokenSheet() }
        }

    @Test
    fun darkSheet() =
        captureRoboImage("src/test/screenshots/token_sheet_dark.png") {
            LearnmateTheme(darkTheme = true, compact = false) { TokenSheet() }
        }
}
