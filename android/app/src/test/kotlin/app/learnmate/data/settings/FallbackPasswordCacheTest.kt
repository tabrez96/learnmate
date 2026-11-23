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
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File
import java.io.IOException
import java.util.Base64

class FallbackPasswordCacheTest {
    @TempDir
    lateinit var tempDir: File

    private fun store(job: Job): DataStore<Preferences> =
        PreferenceDataStoreFactory.create(
            scope = CoroutineScope(Dispatchers.IO + job),
            produceFile = { File(tempDir, "settings.preferences_pb") },
        )

    @Test
    fun verifiesRightAndRejectsWrong() =
        runTest {
            val job = SupervisorJob()
            val cache = FallbackPasswordCache(store(job))
            cache.store("correct horse")
            assertTrue(cache.verify("correct horse"))
            assertFalse(cache.verify("wrong"))
            job.cancelAndJoin()
        }

    @Test
    fun storesOnlySaltedHash() =
        runTest {
            val job = SupervisorJob()
            val dataStore = store(job)
            val cache = FallbackPasswordCache(dataStore)
            cache.store("correct horse")
            val entries =
                dataStore.data
                    .first()
                    .asMap()
                    .mapKeys { it.key.name }
            assertEquals(setOf("fallback_password_hash"), entries.keys)
            val first = entries.getValue("fallback_password_hash") as String
            assertFalse(first.contains("correct horse"))
            val parts = first.split(":")
            assertEquals(2, parts.size)
            parts.forEach { Base64.getDecoder().decode(it) }

            cache.store("correct horse")
            val second =
                dataStore.data.first()[
                    androidx.datastore.preferences.core
                        .stringPreferencesKey("fallback_password_hash"),
                ]
            assertNotEquals(first, second)
            job.cancelAndJoin()
        }

    @Test
    fun changeReplacesOldPassword() =
        runTest {
            val job = SupervisorJob()
            val cache = FallbackPasswordCache(store(job))
            cache.store("first")
            cache.store("second")
            assertTrue(cache.verify("second"))
            assertFalse(cache.verify("first"))
            job.cancelAndJoin()
        }

    @Test
    fun nothingStoredRejects() =
        runTest {
            val job = SupervisorJob()
            val cache = FallbackPasswordCache(store(job))
            assertFalse(cache.verify(""))
            assertFalse(cache.verify("x"))
            assertFalse(cache.isSet.first())
            cache.store("x")
            assertTrue(cache.isSet.first())
            job.cancelAndJoin()
        }

    @Test
    fun readFailureRejects() =
        runTest {
            val failing =
                object : DataStore<Preferences> {
                    override val data: Flow<Preferences> = flow { throw IOException("read failed") }

                    override suspend fun updateData(transform: suspend (Preferences) -> Preferences) = emptyPreferences()
                }
            val cache = FallbackPasswordCache(failing)
            assertFalse(cache.verify("anything"))
            assertFalse(cache.isSet.first())
        }
}
