package app.learnmate.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

class AppearanceRepository(
    private val dataStore: DataStore<Preferences>,
) {
    val appearance: Flow<Appearance> =
        dataStore.data
            .catch { error ->
                if (error !is IOException) throw error
                emit(emptyPreferences())
            }.map { Appearance.fromStored(it[AppearanceKey]) }

    suspend fun setAppearance(appearance: Appearance) {
        dataStore.edit { it[AppearanceKey] = appearance.storedValue }
    }

    private companion object {
        val AppearanceKey = stringPreferencesKey("appearance")
    }
}
