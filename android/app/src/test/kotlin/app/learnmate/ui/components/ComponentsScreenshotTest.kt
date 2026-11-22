package app.learnmate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.unit.dp
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.pageBackground
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w1000dp-h700dp-mdpi")
class ComponentsScreenshotTest {
    @get:Rule val compose = createComposeRule()

    /** Captures the content on the page background in light, then dark, cropped to the content. */
    private fun snap(
        name: String,
        content: @Composable () -> Unit,
    ) {
        var dark by mutableStateOf(false)
        compose.setContent {
            LearnmateTheme(darkTheme = dark, compact = false) {
                Box(
                    Modifier
                        .testTag("shot")
                        .pageBackground(LearnmateTheme.colors.paper, LearnmateTheme.surfaces)
                        .padding(32.dp),
                ) { content() }
            }
        }
        compose.onNodeWithTag("shot").captureRoboImage("src/test/screenshots/components/${name}_light.png")
        dark = true
        compose.waitForIdle()
        compose.onNodeWithTag("shot").captureRoboImage("src/test/screenshots/components/${name}_dark.png")
    }

    @Test
    fun buttons() =
        snap("buttons") {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                PrimaryButton("Continue the lesson", {})
                SecondaryButton("Start another session", {})
                GhostButton("I'm done: ask a parent to end", {})
                PrimaryButton("Finish setup", {}, enabled = false)
            }
        }

    @Test
    fun card() =
        snap("card") {
            LearnmateCard(Modifier.width(420.dp)) {
                Text("Today's plan", color = LearnmateTheme.colors.ink, style = MaterialTheme.typography.titleLarge)
                Text("Three steps, about 25 minutes.", color = LearnmateTheme.colors.inkSoft, style = MaterialTheme.typography.bodyMedium)
            }
        }

    @Test
    fun heroCard() =
        snap("heroCard") {
            GradientHeroCard(Modifier.width(700.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    LearnmateChip("Today", ChipTone.OnHero)
                    LearnmateChip("No session yet", ChipTone.Warn)
                }
                Text("Hi Omar! Ready to learn?", style = MaterialTheme.typography.headlineLarge)
                Text("Level 4 · 70% to the next level", style = MaterialTheme.typography.bodyMedium)
                LearnmateProgressBar(0.7f, track = Color.White.copy(alpha = 0.3f), fill = LearnmateTheme.gradients.gold)
                HeroButton("Start today's session", {})
            }
        }

    @Test
    fun statTile() =
        snap("statTile") {
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                StatTile("6", "Day streak", Modifier.width(220.dp), icon = "🔥")
                StatTile("82% B", "Average grade", Modifier.width(220.dp))
            }
        }

    @Test
    fun stepRows() =
        snap("stepRows") {
            Column(Modifier.width(420.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                StepRow(1, "Warm-up quiz", "Five quick questions", StepState.Done, trailing = { LearnmateChip("+10", ChipTone.Ok) })
                StepRow(2, "Lesson with your mentor", "Learn today's chapter", StepState.Current)
                StepRow(3, "Short challenge", "Check what stuck", StepState.Upcoming)
            }
        }

    @Test
    fun progressBar() =
        snap("progressBar") {
            Column(Modifier.width(400.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                LearnmateProgressBar(0f)
                LearnmateProgressBar(0.4f)
                LearnmateProgressBar(1f)
            }
        }

    @Test
    fun chips() =
        snap("chips") {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    LearnmateChip("Today", ChipTone.Blue)
                    LearnmateChip("90% A", ChipTone.Ok)
                    LearnmateChip("No session yet", ChipTone.Warn)
                    LearnmateChip("45% F", ChipTone.Bad)
                    LearnmateChip("Missed", ChipTone.Missed)
                }
                GradientHeroCard(Modifier.width(200.dp)) { LearnmateChip("Today", ChipTone.OnHero) }
            }
        }

    @Test
    fun sessionPill() = snap("sessionPill") { SessionPill(24) }

    @Test
    fun themeSwitch() =
        snap("themeSwitch") {
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                ThemeSwitch(dark = false, {})
                ThemeSwitch(dark = true, {})
            }
        }

    @Test
    fun topBar() =
        snap("topBar") {
            Column(Modifier.width(900.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                LearnmateTopBar {
                    ThemeSwitch(false, {})
                    GhostButton("Settings", {})
                }
                LearnmateTopBar {
                    ThemeSwitch(false, {})
                    SessionPill(24)
                }
            }
        }

    @Test
    fun focusRing() =
        snap("focusRing") {
            val blue = LearnmateTheme.colors.blue
            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                Box(
                    Modifier
                        .size(200.dp, 52.dp)
                        .focusRing(true, blue, LearnmateShapes.button)
                        .background(LearnmateTheme.gradients.brand, LearnmateShapes.button),
                )
                Box(
                    Modifier
                        .size(90.dp, 44.dp)
                        .focusRing(true, blue, LearnmateShapes.pill)
                        .background(LearnmateTheme.colors.paper, LearnmateShapes.pill),
                )
            }
        }
}
