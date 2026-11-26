package app.learnmate.ui.firstrun

import androidx.compose.runtime.Composable
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
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
class FirstRunScreenshotTest {
    @get:Rule val compose = createComposeRule()

    private val state =
        FirstRunUiState(
            loading = false,
            childName = "Omar",
            grade = 7,
            familySaved = true,
            telegramConnected = true,
            telegramHandle = "omars_parent",
        )

    private fun snap(
        name: String,
        dark: Boolean,
        compact: Boolean,
        s: FirstRunUiState = state,
    ) {
        compose.setContent { Screen(s, dark, compact) }
        compose.onRoot().captureRoboImage("src/test/screenshots/firstrun/$name.png")
    }

    @Composable
    private fun Screen(
        s: FirstRunUiState,
        dark: Boolean,
        compact: Boolean,
    ) = LearnmateTheme(darkTheme = dark, compact = compact) {
        FirstRunScreen(s, dark, {}, {}, {}, {}, {}, {}, {}, {}, {})
    }

    @Test
    fun firstRunLight() = snap("firstRunLight", dark = false, compact = false)

    @Test
    fun firstRunDark() = snap("firstRunDark", dark = true, compact = false)

    @Test
    @Config(qualifiers = "w400dp-h1900dp-mdpi")
    fun firstRunPhoneLight() = snap("firstRunPhoneLight", dark = false, compact = true)

    @Test
    fun firstRunWaitingLight() =
        snap(
            "firstRunWaitingLight",
            dark = false,
            compact = false,
            s = state.copy(telegramConnected = false, linkCode = "3f9a1c2e7b4d6a08"),
        )
}
