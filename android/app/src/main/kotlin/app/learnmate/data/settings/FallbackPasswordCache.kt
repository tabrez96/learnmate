package app.learnmate.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import app.learnmate.data.session.SecretHasher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.io.IOException

/** Salted hash of the fallback password, so a session can be force-ended while the server is unreachable. */
class FallbackPasswordCache(
    private val dataStore: DataStore<Preferences>,
) {
    private val prefs: Flow<Preferences> =
        dataStore.data.catch { error ->
            if (error !is IOException) throw error
            emit(emptyPreferences())
        }

    val isSet: Flow<Boolean> = prefs.map { it[HashKey] != null }

    /** Call when the fallback password is set (first run) or changed (Settings). Stores only "salt:hash". */
    suspend fun store(password: String) {
        val hash = withContext(Dispatchers.Default) { SecretHasher.hash(password) }
        dataStore.edit { it[HashKey] = hash }
    }

    /** False when nothing is cached or the cache can't be read. */
    suspend fun verify(password: String): Boolean {
        val stored = prefs.first()[HashKey] ?: return false
        return withContext(Dispatchers.Default) { SecretHasher.verify(password, stored) }
    }

    private companion object {
        val HashKey = stringPreferencesKey("fallback_password_hash")
    }
}
