package app.learnmate.ui.mentor

import androidx.compose.runtime.Composable
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
import app.learnmate.session.mentor.ChatItem
import app.learnmate.session.mentor.MentorUiState
import app.learnmate.ui.theme.LearnmateTheme
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w1280dp-h800dp-mdpi")
class MentorScreenScreenshotTest {
    @get:Rule val compose = createComposeRule()

    private val source = "From: Science notes, p.32"

    private val state =
        MentorUiState(
            loading = false,
            ready = true,
            topic = "Photosynthesis",
            stepTitles =
                listOf(
                    "What plants need",
                    "Where it happens",
                    "Chlorophyll",
                    "The word equation",
                    "Day and night",
                    "Quick review",
                ),
            stepIndex = 2,
            teachingFrom = "Teaching from: Science notes, chapter 4",
            outsideAllowed = true,
            items =
                listOf(
                    ChatItem.Student("1", "Green!"),
                    ChatItem.Mentor("2", "Yes! +10 That's why leaves look green.", source),
                    ChatItem.Mentor(
                        "3",
                        "Chlorophyll soaks up blue and red light. Green bounces off, so that's what you see.",
                        source,
                        hasVisual = true,
                    ),
                    ChatItem.Student("4", "Where in the leaf is the chlorophyll?"),
                    ChatItem.Outside("5", "Mostly in the palisade cells, near the top of the leaf.", "Source: britannica.com"),
                ),
        )

    private fun snap(
        name: String,
        dark: Boolean,
    ) {
        compose.setContent { Screen(dark) }
        compose.onRoot().captureRoboImage("src/test/screenshots/mentor/$name.png")
    }

    @Composable
    private fun Screen(dark: Boolean) =
        LearnmateTheme(darkTheme = dark, compact = false) {
            MentorScreen(state, dark, 26, {}, {}, { _, _ -> }, {}, {}, { _, _ -> }, {}, {}, {})
        }

    @Test
    fun mentorLight() = snap("mentorLight", dark = false)

    @Test
    fun mentorDark() = snap("mentorDark", dark = true)
}
