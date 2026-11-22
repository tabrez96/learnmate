package app.learnmate.ui.theme

import android.graphics.drawable.AdaptiveIconDrawable
import androidx.test.core.app.ApplicationProvider
import app.learnmate.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class LauncherIconTest {
    @Test
    fun manifestUsesAdaptiveIcon() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        assertEquals(R.mipmap.ic_launcher, context.applicationInfo.icon)
        assertTrue(context.getDrawable(R.mipmap.ic_launcher) is AdaptiveIconDrawable)
        assertTrue(context.getDrawable(R.mipmap.ic_launcher_round) is AdaptiveIconDrawable)
    }
}
