package app.learnmate.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File
import java.io.IOException

class AppearanceRepositoryTest {
    @TempDir
    lateinit var tempDir: File

    /** Each repository gets its own DataStore scope; DataStore allows only one active instance per file. */
    private fun repository(job: Job) =
        AppearanceRepository(
            PreferenceDataStoreFactory.create(
                scope = CoroutineScope(Dispatchers.IO + job),
                produceFile = { File(tempDir, "settings.preferences_pb") },
            ),
        )

    @Test
    fun defaultsSwitchesAndPersists() =
        runTest {
            val first = SupervisorJob()
            val repository = repository(first)
            assertEquals(Appearance.MatchDevice, repository.appearance.first())
            for (mode in listOf(Appearance.Light, Appearance.MatchDevice, Appearance.Dark)) {
                repository.setAppearance(mode)
                assertEquals(mode, repository.appearance.first())
            }
            first.cancelAndJoin()

            val second = SupervisorJob()
            assertEquals(Appearance.Dark, repository(second).appearance.first())
            second.cancelAndJoin()
        }

    @Test
    fun failedReadFallsBackToMatchDevice() =
        runTest {
            val failing =
                object : DataStore<Preferences> {
                    override val data: Flow<Preferences> = flow { throw IOException("read failed") }

                    override suspend fun updateData(transform: suspend (Preferences) -> Preferences) = emptyPreferences()
                }
            assertEquals(Appearance.MatchDevice, AppearanceRepository(failing).appearance.first())
        }

    @Test
    fun isDarkFollowsChoice() {
        assertFalse(Appearance.Light.isDark(true))
        assertTrue(Appearance.Dark.isDark(false))
        assertTrue(Appearance.MatchDevice.isDark(true))
        assertFalse(Appearance.MatchDevice.isDark(false))
        assertEquals(Appearance.MatchDevice, Appearance.fromStored("bogus"))
    }
}
